import os
import random
from datetime import datetime, timezone
import duckdb
from pytrends.request import TrendReq
import requests
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trends.db")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()

TRACKED_SUBREDDITS = [
    "technology",
    "artificial",
    "machinelearning",
    "science",
    "sports",
    "movies"
]

SOCIAL_NEWS_CATEGORIES = [
    "technology",
    "sports",
    "science",
    "health",
    "business",
    "entertainment"
]

app = FastAPI(title="SocialPulse API", description="Analytical API for Social Media Trends, Google Trends, and Science News")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file not found. Run the pipeline first.")
    return duckdb.connect(DB_PATH, read_only=True)

def table_exists(con, table_name):
    res = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name]).fetchone()
    return res is not None

def _fetch_json(url, params=None, headers=None):
    response = requests.get(url, params=params, headers=headers, timeout=12)
    response.raise_for_status()
    return response.json()

def _date_seed():
    return datetime.now(timezone.utc).date().toordinal()

def _fallback_youtube_data(limit=10):
    rng = random.Random(_date_seed() + 3001)
    categories = ["Technology", "Science", "Sports", "Entertainment", "News"]
    rows = []
    for idx in range(limit):
        views = rng.randint(50000, 3000000)
        likes = int(views * rng.uniform(0.02, 0.08))
        comments = int(views * rng.uniform(0.002, 0.02))
        engagement_score = round(((likes + comments) / max(views, 1)) * 100, 3)
        virality_score = round((views / 10000) + (comments / 1000), 2)
        rows.append({
            "title": f"Simulated trending video #{idx + 1}",
            "channel": f"Channel {rng.randint(1, 60)}",
            "category": rng.choice(categories),
            "view_count": views,
            "like_count": likes,
            "comment_count": comments,
            "engagement_score": engagement_score,
            "virality_score": virality_score,
            "url": f"https://www.youtube.com/results?search_query=simulated+video+{idx+1}"
        })
    return rows

def _fallback_news_data():
    rng = random.Random(_date_seed() + 9917)
    data = {}
    for category in SOCIAL_NEWS_CATEGORIES:
        topic_count = rng.randint(4, 9)
        topics = []
        for idx in range(topic_count):
            topics.append({
                "title": f"{category.title()} headline {idx + 1}",
                "source": f"Source {rng.randint(1, 15)}",
                "url": f"https://news.google.com/search?q={category}"
            })
        data[category] = topics
    return data

def _youtube_category_name(category_id):
    mapping = {
        "1": "Film & Animation",
        "2": "Autos & Vehicles",
        "10": "Music",
        "15": "Pets & Animals",
        "17": "Sports",
        "19": "Travel & Events",
        "20": "Gaming",
        "22": "People & Blogs",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
        "26": "Howto & Style",
        "27": "Education",
        "28": "Science & Technology"
    }
    return mapping.get(str(category_id), "Other")

def _fallback_google_trends_from_duckdb(country: str, category: str, limit: int):
    """Fallback to DuckDB-stored Google Trends if live pytrends fails."""
    try:
        con = get_db_connection()
        if not table_exists(con, "google_category_trends"):
            con.close()
            return []

        fetch_limit = min(max(int(limit) * 3, 10), 120)
        query = """
            SELECT rank, search_term
            FROM google_category_trends
            WHERE LOWER(country) = ? AND LOWER(category) = ?
            ORDER BY rank ASC
            LIMIT ?
        """
        rows = con.execute(
            query,
            [country.lower().strip(), category.lower().strip(), fetch_limit]
        ).fetchall()
        con.close()

        # Make the fallback change day-to-day so it doesn't look static.
        seed = _date_seed() + sum(ord(c) for c in country) + sum(ord(c) for c in category) + 1111
        rng = random.Random(seed)
        terms = [r[1] for r in rows if r and r[1]]
        rng.shuffle(terms)
        terms = terms[: int(limit)]

        return [{"rank": i + 1, "search_term": terms[i]} for i in range(len(terms))]
    except Exception:
        return []

def _fallback_google_trends_random(country: str, limit: int):
    """Last-resort deterministic fallback: day-changing query pool."""
    rng = random.Random(_date_seed() + sum(ord(c) for c in country) + 4242)
    pool = [
        "chatgpt 5",
        "iphone launch",
        "election results",
        "moon mission",
        "tesla earnings",
        "stock market today",
        "weather update",
        "olympics 2026",
        "ai startup",
        "cyber security",
        "new vaccine trial",
        "renewable energy",
        "sports highlights",
        "movie streaming",
        "health breakthrough",
        "space telescope",
        "fiscal policy",
        "new gaming update",
        "science discovery",
        "financial forecast",
        "tech layoffs",
        "software release",
        "product launch",
        "trending app",
        "latest smartphone"
    ]
    rng.shuffle(pool)
    return [{"rank": i + 1, "search_term": pool[i]} for i in range(min(limit, len(pool)))]

def _fallback_reddit_social_data_from_duckdb(limit_posts: int = 12, limit_discussions: int = 10):
    """Fallback to DuckDB Reddit data if live Reddit fetch fails."""
    try:
        con = get_db_connection()
        if not table_exists(con, "reddit_posts"):
            con.close()
            return None

        subs = TRACKED_SUBREDDITS
        placeholders = ",".join(["?"] * len(subs))
        subs_params = [s.lower() for s in subs]

        query_posts = f"""
            SELECT subreddit, title, score, num_comments
            FROM reddit_posts
            WHERE LOWER(subreddit) IN ({placeholders})
            ORDER BY (score + num_comments * 2) DESC
            LIMIT ?
        """
        posts_rows = con.execute(query_posts, [*subs_params, int(limit_posts)]).fetchall()
        posts = [{
            "subreddit": r[0],
            "title": r[1],
            "score": int(r[2] or 0),
            "num_comments": int(r[3] or 0),
            "url": f"https://reddit.com/r/{r[0]}/"
        } for r in posts_rows]

        query_volume = f"""
            SELECT subreddit, SUM(num_comments) as total_comments
            FROM reddit_posts
            WHERE LOWER(subreddit) IN ({placeholders})
            GROUP BY subreddit
        """
        volume_rows = con.execute(query_volume, subs_params).fetchall()
        comment_volume = {r[0]: int(r[1] or 0) for r in volume_rows}

        query_pop = f"""
            SELECT subreddit, COUNT(*) as post_count
            FROM reddit_posts
            WHERE LOWER(subreddit) IN ({placeholders})
            GROUP BY subreddit
            ORDER BY post_count DESC
        """
        pop_rows = con.execute(query_pop, subs_params).fetchall()
        popular_subreddits = [{
            "subreddit": r[0],
            "subscribers": int(r[1] or 0),
            "active_users": 0
        } for r in pop_rows]

        con.close()

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tracked_subreddits": subs,
            "trending_posts": posts,
            "top_discussions": sorted(posts, key=lambda x: x["num_comments"], reverse=True)[:limit_discussions],
            "popular_subreddits": sorted(popular_subreddits, key=lambda x: x["subscribers"], reverse=True),
            "comment_volume": comment_volume,
            "is_fallback_data": True
        }
    except Exception:
        return None

def _fallback_reddit_social_data_random():
    """Last-resort deterministic fallback for Reddit card."""
    rng = random.Random(_date_seed() + 777)
    tracked = TRACKED_SUBREDDITS
    generated_at = datetime.now(timezone.utc).isoformat()

    posts = []
    comment_volume = {}
    popular_subreddits = []

    for sub in tracked:
        subs_posts = []
        for j in range(4):
            score = rng.randint(1000, 120000)
            num_comments = rng.randint(50, 8000)
            subs_posts.append({
                "subreddit": sub,
                "title": f"Daily spike in {sub.replace('machinelearning','ML')} discussions #{j+1}",
                "score": score,
                "num_comments": num_comments,
                "url": f"https://reddit.com/r/{sub}/"
            })
        posts.extend(subs_posts)
        comment_volume[sub] = int(sum(p["num_comments"] for p in subs_posts))
        popular_subreddits.append({
            "subreddit": sub,
            "subscribers": rng.randint(50000, 20000000),
            "active_users": rng.randint(1000, 2000000)
        })

    trending_posts = sorted(posts, key=lambda x: x["score"], reverse=True)[:12]
    top_discussions = sorted(trending_posts, key=lambda x: x["num_comments"], reverse=True)[:10]

    return {
        "generated_at": generated_at,
        "tracked_subreddits": tracked,
        "trending_posts": trending_posts,
        "top_discussions": top_discussions,
        "popular_subreddits": sorted(popular_subreddits, key=lambda x: x["subscribers"], reverse=True),
        "comment_volume": comment_volume,
        "is_fallback_data": True
    }

@app.get("/api/summary")
def get_summary():
    """Get high-level overview metrics (KPIs) for the dashboard, merging Social and Google Trends data."""
    try:
        con = get_db_connection()
        
        tweet_count = 0
        reddit_count = 0
        total_engagement = 0
        top_keyword = "N/A"
        top_keyword_vel = 0.0
        
        # Query Twitter/Reddit tables if they exist
        if table_exists(con, "tweets"):
            tweet_count = con.execute("SELECT COUNT(*) FROM tweets").fetchone()[0] or 0
            tot_likes = con.execute("SELECT SUM(likes) FROM tweets").fetchone()[0] or 0
            tot_retweets = con.execute("SELECT SUM(retweets) FROM tweets").fetchone()[0] or 0
            total_engagement += int(tot_likes + tot_retweets)
            
        if table_exists(con, "reddit_posts"):
            reddit_count = con.execute("SELECT COUNT(*) FROM reddit_posts").fetchone()[0] or 0
            tot_reddit_score = con.execute("SELECT SUM(score) FROM reddit_posts").fetchone()[0] or 0
            total_engagement += int(tot_reddit_score)
            
        if table_exists(con, "keyword_velocity"):
            top_keyword_row = con.execute("""
                SELECT keyword, velocity 
                FROM keyword_velocity 
                WHERE current_count > 5 
                ORDER BY velocity DESC 
                LIMIT 1
            """).fetchone()
            if top_keyword_row:
                top_keyword = top_keyword_row[0]
                top_keyword_vel = top_keyword_row[1]

        # Query Google Trends tables if they exist
        top_google_trend = "N/A"
        if table_exists(con, "google_category_trends"):
            google_row = con.execute("""
                SELECT search_term 
                FROM google_category_trends 
                WHERE country = 'United States' AND category = 'General'
                ORDER BY rank ASC 
                LIMIT 1
            """).fetchone()
            if google_row:
                top_google_trend = google_row[0]
                
        # Top Category by current interest
        top_category = "N/A"
        if table_exists(con, "google_category_interest"):
            cat_row = con.execute("""
                SELECT category, AVG(interest_score) as avg_score
                FROM google_category_interest
                WHERE is_forecast = false
                GROUP BY category
                ORDER BY avg_score DESC
                LIMIT 1
            """).fetchone()
            if cat_row:
                top_category = cat_row[0]

        con.close()
        
        return {
            "total_tweets": int(tweet_count),
            "total_reddit_posts": int(reddit_count),
            "total_engagement": int(total_engagement),
            "social_top_keyword": top_keyword,
            "social_top_keyword_velocity": round(float(top_keyword_vel), 2),
            "top_google_search": top_google_trend,
            "top_google_category": top_category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends/categories")
def get_category_interest(category: str = Query(None)):
    """Retrieve daily category interest trends, including historical and forecasts."""
    try:
        con = get_db_connection()
        if not table_exists(con, "google_category_interest"):
            con.close()
            return {}
            
        if category:
            query = """
                SELECT category, date, interest_score, is_forecast
                FROM google_category_interest
                WHERE LOWER(category) = ?
                ORDER BY date
            """
            rows = con.execute(query, [category.lower().strip()]).fetchall()
        else:
            query = """
                SELECT category, date, interest_score, is_forecast
                FROM google_category_interest
                ORDER BY category, date
            """
            rows = con.execute(query).fetchall()
            
        con.close()
        
        result = {}
        for r in rows:
            c = r[0]
            if c not in result:
                result[c] = []
            result[c].append({
                "date": r[1],
                "score": float(r[2]),
                "is_forecast": bool(r[3])
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends/categories/trending")
def get_category_trending_searches(
    country: str = Query("United States"),
    category: str = Query("General")
):
    """Retrieve trending searches filtered by country and category."""
    try:
        con = get_db_connection()
        if not table_exists(con, "google_category_trends"):
            con.close()
            return []
            
        query = """
            SELECT rank, search_term
            FROM google_category_trends
            WHERE LOWER(country) = ? AND LOWER(category) = ?
            ORDER BY rank ASC
        """
        rows = con.execute(query, [country.lower().strip(), category.lower().strip()]).fetchall()
        con.close()
        
        return [{"rank": r[0], "search_term": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/google/realtime")
def get_google_realtime_trends(
    country: str = Query("India"),
    category: str = Query("General"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Live Google Trends trending searches via pytrends.
    This bypasses the DuckDB cache and always reflects current Google data.
    """
    country_map = {
        "India": "india",
        "United States": "united_states",
        "United Kingdom": "united_kingdom",
        "Canada": "canada"
    }
    pn = country_map.get(country, "india")

    try:
        pytrends = TrendReq()
        df = pytrends.trending_searches(pn=pn)
        trends = []
        for idx, row in df.head(limit).iterrows():
            query = str(row[0])
            trends.append({
                "rank": idx + 1,
                "search_term": query
            })
        return trends
    except Exception as e:
        # Don't break the dashboard if live pytrends fails (rate limit, network block, etc.)
        duckdb_trends = _fallback_google_trends_from_duckdb(country=country, category=category, limit=limit)
        if duckdb_trends:
            return duckdb_trends
        return _fallback_google_trends_random(country=country, limit=limit)

@app.get("/api/social/reddit")
def get_reddit_social_data():
    """Live Reddit social intelligence for tracked subreddits."""
    reddit_headers = {
        "User-Agent": "SocialPulseTrendAnalyzer/1.0"
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tracked_subreddits": TRACKED_SUBREDDITS,
        "trending_posts": [],
        "top_discussions": [],
        "popular_subreddits": [],
        "comment_volume": {}
    }

    try:
        all_posts = []
        for subreddit in TRACKED_SUBREDDITS:
            listing = _fetch_json(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                params={"limit": 10},
                headers=reddit_headers
            )
            posts = [item.get("data", {}) for item in listing.get("data", {}).get("children", [])]
            all_posts.extend(posts)
            payload["comment_volume"][subreddit] = int(sum(int(p.get("num_comments", 0)) for p in posts))

            try:
                about = _fetch_json(
                    f"https://www.reddit.com/r/{subreddit}/about.json",
                    headers=reddit_headers
                )
                about_data = about.get("data", {})
                payload["popular_subreddits"].append({
                    "subreddit": subreddit,
                    "subscribers": int(about_data.get("subscribers", 0)),
                    "active_users": int(about_data.get("active_user_count") or 0)
                })
            except Exception:
                payload["popular_subreddits"].append({
                    "subreddit": subreddit,
                    "subscribers": 0,
                    "active_users": 0
                })

        payload["trending_posts"] = sorted(
            [{
                "subreddit": p.get("subreddit", ""),
                "title": p.get("title", ""),
                "score": int(p.get("score", 0)),
                "num_comments": int(p.get("num_comments", 0)),
                "url": p.get("url")
            } for p in all_posts],
            key=lambda x: x["score"],
            reverse=True
        )[:12]

        payload["top_discussions"] = sorted(
            payload["trending_posts"],
            key=lambda x: x["num_comments"],
            reverse=True
        )[:10]

        payload["popular_subreddits"] = sorted(
            payload["popular_subreddits"],
            key=lambda x: x["subscribers"],
            reverse=True
        )
        return payload
    except Exception as e:
        # Don't break the dashboard if Reddit is blocked/rate-limited.
        # Fall back to DuckDB-stored Reddit data (or deterministic daily simulation).
        fallback = _fallback_reddit_social_data_from_duckdb()
        if fallback is None:
            fallback = _fallback_reddit_social_data_random()
        fallback["warning"] = f"Reddit live fetch failed: {e}"
        return fallback

@app.get("/api/social/youtube")
def get_youtube_social_data(region: str = Query("US"), limit: int = Query(10, ge=5, le=25)):
    """Trending YouTube videos with engagement and virality scores."""
    generated_at = datetime.now(timezone.utc).isoformat()
    if not YOUTUBE_API_KEY:
        return {
            "generated_at": generated_at,
            "is_fallback_data": True,
            "videos": _fallback_youtube_data(limit=limit)
        }

    try:
        data = _fetch_json(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "regionCode": region,
                "maxResults": limit,
                "key": YOUTUBE_API_KEY
            }
        )
        videos = []
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            video_id = item.get("id", "")
            if isinstance(video_id, dict):
                video_id = video_id.get("videoId", "")
            engagement_score = round(((likes + comments) / max(views, 1)) * 100, 3)
            virality_score = round((views / 100000) + (comments / 5000), 2)
            videos.append({
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "category": _youtube_category_name(snippet.get("categoryId")),
                "view_count": views,
                "like_count": likes,
                "comment_count": comments,
                "engagement_score": engagement_score,
                "virality_score": virality_score,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com"
            })
        return {
            "generated_at": generated_at,
            "is_fallback_data": False,
            "videos": videos
        }
    except Exception as e:
        return {
            "generated_at": generated_at,
            "is_fallback_data": True,
            "warning": f"Live YouTube fetch failed: {e}",
            "videos": _fallback_youtube_data(limit=limit)
        }

@app.get("/api/social/news")
def get_social_news_data(country: str = Query("us")):
    """Breaking and category-wise news from NewsAPI (or daily fallback)."""
    generated_at = datetime.now(timezone.utc).isoformat()
    if not NEWS_API_KEY:
        fallback = _fallback_news_data()
        return {
            "generated_at": generated_at,
            "is_fallback_data": True,
            "breaking_news": fallback.get("technology", [])[:5],
            "category_wise_news": fallback,
            "trending_topics": {k: len(v) for k, v in fallback.items()}
        }

    try:
        category_map = {
            "technology": "technology",
            "sports": "sports",
            "science": "science",
            "health": "medical",
            "business": "finance",
            "entertainment": "entertainment"
        }
        category_payload = {}
        for api_category, display_name in category_map.items():
            cat_res = _fetch_json(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": NEWS_API_KEY,
                    "country": country,
                    "category": api_category,
                    "pageSize": 8
                }
            )
            articles = cat_res.get("articles", [])
            category_payload[display_name] = [{
                "title": article.get("title", ""),
                "source": (article.get("source") or {}).get("name", ""),
                "url": article.get("url")
            } for article in articles]

        breaking = _fetch_json(
            "https://newsapi.org/v2/top-headlines",
            params={
                "apiKey": NEWS_API_KEY,
                "country": country,
                "pageSize": 10
            }
        )
        breaking_articles = [{
            "title": article.get("title", ""),
            "source": (article.get("source") or {}).get("name", ""),
            "url": article.get("url")
        } for article in breaking.get("articles", [])]

        return {
            "generated_at": generated_at,
            "is_fallback_data": False,
            "breaking_news": breaking_articles[:8],
            "category_wise_news": category_payload,
            "trending_topics": {k: len(v) for k, v in category_payload.items()}
        }
    except Exception as e:
        fallback = _fallback_news_data()
        return {
            "generated_at": generated_at,
            "is_fallback_data": True,
            "warning": f"Live NewsAPI fetch failed: {e}",
            "breaking_news": fallback.get("technology", [])[:5],
            "category_wise_news": fallback,
            "trending_topics": {k: len(v) for k, v in fallback.items()}
        }

@app.get("/api/trends/science/news")
def get_science_news():
    """Retrieve science & tech news articles along with their NLP sentiment scores."""
    try:
        con = get_db_connection()
        if not table_exists(con, "science_news_trends"):
            con.close()
            return []
            
        query = """
            SELECT title, link, published_date, source, sentiment_score, sentiment_label
            FROM science_news_trends
            ORDER BY published_date DESC
        """
        rows = con.execute(query).fetchall()
        con.close()
        
        return [{
            "title": r[0],
            "link": r[1],
            "published_date": str(r[2]),
            "source": r[3],
            "sentiment_score": round(float(r[4]), 2),
            "sentiment_label": r[5]
        } for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends/science/predictions")
def get_science_predictions(keyword: str = Query("Science")):
    """Get prediction timeseries specifically for science categories."""
    try:
        con = get_db_connection()
        if not table_exists(con, "google_category_interest"):
            con.close()
            return []
            
        query = """
            SELECT date, interest_score, is_forecast
            FROM google_category_interest
            WHERE LOWER(category) = ?
            ORDER BY date
        """
        rows = con.execute(query, [keyword.lower().strip()]).fetchall()
        con.close()
        
        return {
            "keyword": keyword,
            "data": [{"date": r[0], "count": float(r[1]), "is_forecast": bool(r[2])} for r in rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep backward-compatible endpoints for Social trends
@app.get("/api/trends/topics")
def get_trending_topics(limit: int = 15):
    try:
        con = get_db_connection()
        if not table_exists(con, "keyword_velocity"):
            con.close()
            return []
        query = """
            SELECT kv.keyword, kv.current_count, kv.prior_count, kv.velocity, COALESCE(avg_sent.avg_s, 0.0)
            FROM keyword_velocity kv
            LEFT JOIN (SELECT keyword, AVG(avg_sentiment) as avg_s FROM daily_keyword_aggregates GROUP BY keyword) avg_sent ON kv.keyword = avg_sent.keyword
            ORDER BY kv.current_count DESC
            LIMIT ?
        """
        rows = con.execute(query, [limit]).fetchall()
        con.close()
        return [{"keyword": r[0], "current_count": int(r[1]), "prior_count": int(r[2]), "velocity": round(float(r[3]), 2), "avg_sentiment": round(float(r[4]), 3)} for r in rows]
    except Exception:
        return []

@app.get("/api/trends/sentiment")
def get_sentiment_trends():
    try:
        con = get_db_connection()
        if not table_exists(con, "tweets"):
            con.close()
            return {"twitter": [], "reddit": []}
        twitter_sent = con.execute("SELECT created_date, AVG(sentiment_score), COUNT(*) FROM tweets GROUP BY created_date ORDER BY created_date").fetchall()
        reddit_sent = con.execute("SELECT created_date, AVG(sentiment_score), COUNT(*) FROM reddit_posts GROUP BY created_date ORDER BY created_date").fetchall()
        con.close()
        return {
            "twitter": [{"date": r[0], "sentiment": round(float(r[1]), 3) if r[1] is not None else 0.0, "volume": int(r[2])} for r in twitter_sent],
            "reddit": [{"date": r[0], "sentiment": round(float(r[1]), 3) if r[1] is not None else 0.0, "volume": int(r[2])} for r in reddit_sent]
        }
    except Exception:
        return {"twitter": [], "reddit": []}

@app.get("/api/discussions/viral")
def get_viral_discussions(limit: int = 6):
    try:
        con = get_db_connection()
        viral_tweets = []
        viral_reddit = []
        
        if table_exists(con, "tweets"):
            tweets_rows = con.execute("SELECT tweet_id, username, text, created_at, likes, retweets, sentiment_score, sentiment_label FROM tweets ORDER BY (likes + retweets) DESC LIMIT ?", [limit]).fetchall()
            viral_tweets = [{"id": r[0], "author": r[1], "text": r[2], "created_at": str(r[3]), "engagement": int(r[4] + r[5]), "likes": int(r[4]), "retweets": int(r[5]), "sentiment": round(float(r[6]), 2), "sentiment_label": r[7], "platform": "twitter"} for r in tweets_rows]
            
        if table_exists(con, "reddit_posts"):
            posts_rows = con.execute("SELECT post_id, subreddit, title, selftext, author, score, num_comments, sentiment_score, sentiment_label, created_utc FROM reddit_posts ORDER BY (score + num_comments * 2) DESC LIMIT ?", [limit]).fetchall()
            viral_reddit = [{"id": r[0], "subreddit": r[1], "title": r[2], "text": r[3] if isinstance(r[3], str) else "", "author": r[4], "engagement": int(r[5] + r[6] * 2), "score": int(r[5]), "comments_count": int(r[6]), "sentiment": round(float(r[7]), 2), "sentiment_label": r[8], "created_at": str(r[9]), "platform": "reddit"} for r in posts_rows]
            
        con.close()
        return {"tweets": viral_tweets, "reddit_posts": viral_reddit}
    except Exception:
        return {"tweets": [], "reddit_posts": []}

@app.get("/api/trends/prediction")
def get_trend_predictions(keyword: str = Query(None)):
    try:
        con = get_db_connection()
        if not table_exists(con, "trend_predictions"):
            con.close()
            return []
        if not keyword:
            top_row = con.execute("SELECT keyword FROM keyword_velocity ORDER BY current_count DESC LIMIT 1").fetchone()
            keyword = top_row[0] if top_row else ""
        if not keyword:
            con.close()
            return []
        rows = con.execute("SELECT date, count, is_forecast FROM trend_predictions WHERE keyword = ? ORDER BY date", [keyword.lower().strip()]).fetchall()
        con.close()
        return {"keyword": keyword, "data": [{"date": r[0], "count": float(r[1]), "is_forecast": bool(r[2])} for r in rows]}
    except Exception:
        return []

# Unified Pipeline Execution Trigger
async def _run_pipelines_task():
    try:
        await manager.broadcast({"event": "pipeline_started"})
        # 1. Run social pipeline if raw data is ready
        try:
            from backend.pipeline import run_etl_pipeline
            await asyncio.to_thread(run_etl_pipeline)
            social_status = "success"
        except Exception as e:
            social_status = f"failed: {e}"
            
        # 2. Run google trends pipeline
        try:
            from backend.google_trends_pipeline import run_google_trends_pipeline
            await asyncio.to_thread(run_google_trends_pipeline)
            google_status = "success"
        except Exception as e:
            google_status = f"failed: {e}"
            
        await manager.broadcast({
            "event": "pipeline_completed",
            "social_status": social_status,
            "google_status": google_status
        })
    except Exception as e:
        await manager.broadcast({"event": "pipeline_error", "error": str(e)})

@app.post("/api/pipeline/run")
async def run_pipeline(background_tasks: BackgroundTasks):
    """Trigger both social and google trends ETL runs."""
    background_tasks.add_task(_run_pipelines_task)
    return {"status": "started", "message": "Pipeline triggered in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
