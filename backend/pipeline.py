import os
import re
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter

# Set path relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "data", "trends.db")

# Fallback basic stop words to avoid external network dependencies during NLTK download
STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", 
    "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", 
    "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", 
    "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", 
    "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", 
    "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", 
    "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", 
    "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", 
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "d", "ll", 
    "m", "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven", 
    "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won", "wouldn",
    "us", "get", "like", "would", "discussion", "thoughts", "below", "let", "know", "discussion on",
    "post", "comment"
}

# Lexicon-based sentiment fallback (in case TextBlob fails to download its corpora on user's machine)
POSITIVE_WORDS = {
    "love", "amazing", "great", "excellent", "good", "beautiful", "wonderful", "fantastic", "breakthrough",
    "productive", "future", "success", "recommend", "benefit", "efficient", "happy", "excited", "progress",
    "improvement", "smart", "win", "improved", "best", "super", "cool", "innovative", "revolution", "rally"
}

NEGATIVE_WORDS = {
    "hate", "terrible", "bad", "worst", "crash", "inflation", "recession", "layoffs", "brutal", "scary",
    "concerning", "ruining", "annoying", "lonely", "disconnected", "worry", "worried", "hack", "hacked",
    "hallucination", "hallucinations", "failed", "expensive", "inaction", "destroy", "destroying", "useless"
}

def analyze_sentiment(text):
    """
    NLP Sentiment Analysis.
    Attempts to use TextBlob. If TextBlob is not fully configured, falls back to a lexicon-based score.
    Returns: (score, label) where score is in [-1.0, 1.0] and label is Positive/Neutral/Negative
    """
    if not isinstance(text, str):
        return 0.0, "Neutral"
    
    # Try using TextBlob
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        score = blob.sentiment.polarity
    except Exception:
        # Lexicon Fallback
        words = re.findall(r'\w+', text.lower())
        pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / total
            
    # Classify label
    if score > 0.05:
        label = "Positive"
    elif score < -0.05:
        label = "Negative"
    else:
        label = "Neutral"
        
    return float(score), label

def clean_text(text):
    """Clean text by removing links, special characters, and extra spaces."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE) # remove URLs
    text = re.sub(r"@\w+", "", text) # remove handles
    text = re.sub(r"[^\w\s#]", "", text) # remove special characters except hashtags
    text = re.sub(r"\s+", " ", text).strip() # normalize spaces
    return text.lower()

def extract_keywords_from_text(text, custom_keywords=None):
    """
    Extracts hashtags and meaningful keywords from text.
    Filters out stop words and short terms.
    """
    cleaned = clean_text(text)
    words = cleaned.split()
    extracted = []
    
    # Track custom multi-word phrases if specified
    if custom_keywords:
        for kw in custom_keywords:
            if kw.lower() in cleaned:
                extracted.append(kw)
                
    for word in words:
        # If it's a hashtag, extract it
        if word.startswith("#") and len(word) > 2:
            extracted.append(word)
        # Otherwise, check if it's a clean keyword
        elif len(word) > 3 and word not in STOP_WORDS and not word.startswith("#"):
            extracted.append(word)
            
    return list(set(extracted))

def forecast_trend(historical_counts, forecast_days=5):
    """
    Simple Timeseries Forecasting using linear regression.
    Given a list of counts, projects the next few days.
    """
    if len(historical_counts) < 3:
        # Not enough data to forecast, return flatline
        val = historical_counts[-1] if len(historical_counts) > 0 else 0
        return [val] * forecast_days
    
    x = np.arange(len(historical_counts))
    y = np.array(historical_counts)
    
    # Fit line: y = m*x + c
    slope, intercept = np.polyfit(x, y, 1)
    
    forecast = []
    for i in range(forecast_days):
        next_x = len(historical_counts) + i
        pred = slope * next_x + intercept
        forecast.append(max(0, round(pred, 1))) # Counts cannot be negative
    return forecast

def run_etl_pipeline():
    print("--- Starting Trend Analyzer ETL Pipeline ---")
    
    # Ensure database folder exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Connect to DuckDB
    con = duckdb.connect(DB_PATH)
    
    # Check if raw files exist
    tweets_path = os.path.join(RAW_DIR, "tweets.csv")
    reddit_posts_path = os.path.join(RAW_DIR, "reddit_posts.csv")
    reddit_comments_path = os.path.join(RAW_DIR, "reddit_comments.csv")
    
    if not (os.path.exists(tweets_path) and os.path.exists(reddit_posts_path) and os.path.exists(reddit_comments_path)):
        print(f"Error: Raw data files not found in {RAW_DIR}")
        print("Please run mock_data_generator.py first to bootstrap datasets.")
        con.close()
        return
    
    # 1. Process Twitter Data
    print("Processing tweets...")
    df_tweets = pd.read_csv(tweets_path)
    # Apply sentiment analysis
    sentiments = [analyze_sentiment(txt) for txt in df_tweets["text"]]
    df_tweets["sentiment_score"] = [s[0] for s in sentiments]
    df_tweets["sentiment_label"] = [s[1] for s in sentiments]
    # Standardize dates
    df_tweets["created_at"] = pd.to_datetime(df_tweets["created_at"])
    df_tweets["created_date"] = df_tweets["created_at"].dt.date.astype(str)
    
    # 2. Process Reddit Posts
    print("Processing Reddit posts...")
    df_posts = pd.read_csv(reddit_posts_path)
    sentiments_posts = [analyze_sentiment(f"{t} {s}") for t, s in zip(df_posts["title"], df_posts["selftext"].fillna(""))]
    df_posts["sentiment_score"] = [s[0] for s in sentiments_posts]
    df_posts["sentiment_label"] = [s[1] for s in sentiments_posts]
    df_posts["created_utc"] = pd.to_datetime(df_posts["created_utc"])
    df_posts["created_date"] = df_posts["created_utc"].dt.date.astype(str)
    
    # 3. Process Reddit Comments
    print("Processing Reddit comments...")
    df_comments = pd.read_csv(reddit_comments_path)
    sentiments_comments = [analyze_sentiment(b) for b in df_comments["body"]]
    df_comments["sentiment_score"] = [s[0] for s in sentiments_comments]
    df_comments["sentiment_label"] = [s[1] for s in sentiments_comments]
    df_comments["created_utc"] = pd.to_datetime(df_comments["created_utc"])
    df_comments["created_date"] = df_comments["created_utc"].dt.date.astype(str)
    
    # Write processed DataFrames to DuckDB tables
    print("Writing processed tables to DuckDB...")
    con.execute("CREATE OR REPLACE TABLE tweets AS SELECT * FROM df_tweets")
    con.execute("CREATE OR REPLACE TABLE reddit_posts AS SELECT * FROM df_posts")
    con.execute("CREATE OR REPLACE TABLE reddit_comments AS SELECT * FROM df_comments")
    
    # 4. Keyword and Topic Extraction
    print("Extracting keywords and generating timeseries...")
    # List of key phrases we explicitly track
    tracked_topics = ["chatgpt", "ai", "crypto", "bitcoin", "ethereum", "inflation", "recession", "remote work", "wfh", "quantum computing", "quantum", "climate change"]
    
    keyword_rows = []
    
    # Process tweets keywords
    for _, row in df_tweets.iterrows():
        keywords = extract_keywords_from_text(row["text"], tracked_topics)
        engagement = int(row["likes"]) + int(row["retweets"])
        for kw in keywords:
            keyword_rows.append({
                "keyword": kw.lower(),
                "created_date": row["created_date"],
                "source": "twitter",
                "sentiment_score": row["sentiment_score"],
                "engagement": engagement
            })
            
    # Process reddit posts keywords
    for _, row in df_posts.iterrows():
        text_comb = f"{row['title']} {row['selftext']}"
        keywords = extract_keywords_from_text(text_comb, tracked_topics)
        engagement = int(row["score"]) + int(row["num_comments"]) * 2
        for kw in keywords:
            keyword_rows.append({
                "keyword": kw.lower(),
                "created_date": row["created_date"],
                "source": "reddit_post",
                "sentiment_score": row["sentiment_score"],
                "engagement": engagement
            })
            
    df_keywords = pd.DataFrame(keyword_rows)
    con.execute("CREATE OR REPLACE TABLE keyword_mentions AS SELECT * FROM df_keywords")
    
    # 5. Precompute aggregates for fast API access
    print("Computing metrics and analytical aggregates...")
    
    # A. Topic Daily Aggregates (volume, sentiment, engagement)
    con.execute("""
        CREATE OR REPLACE TABLE daily_keyword_aggregates AS 
        SELECT 
            keyword, 
            created_date,
            COUNT(*) as mention_count,
            AVG(sentiment_score) as avg_sentiment,
            SUM(engagement) as total_engagement
        FROM keyword_mentions
        GROUP BY keyword, created_date
    """)
    
    # B. Keyword growth velocity
    # Let's define the current period as the last 5 days and the baseline as the 5 days prior.
    # Velocity = (count_current - count_prior) / (count_prior + 1)
    max_date_str = con.execute("SELECT MAX(created_date) FROM keyword_mentions").fetchone()[0]
    max_date = datetime.strptime(max_date_str, "%Y-%m-%d")
    
    current_start = (max_date - timedelta(days=4)).strftime("%Y-%m-%d")
    prior_end = (max_date - timedelta(days=5)).strftime("%Y-%m-%d")
    prior_start = (max_date - timedelta(days=9)).strftime("%Y-%m-%d")
    
    print(f"Calculating growth velocity comparing current [{current_start} to {max_date_str}] vs prior [{prior_start} to {prior_end}]...")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE keyword_velocity AS
        WITH current_period AS (
            SELECT keyword, COUNT(*) as current_count
            FROM keyword_mentions
            WHERE created_date >= '{current_start}'
            GROUP BY keyword
        ),
        prior_period AS (
            SELECT keyword, COUNT(*) as prior_count
            FROM keyword_mentions
            WHERE created_date >= '{prior_start}' AND created_date <= '{prior_end}'
            GROUP BY keyword
        )
        SELECT 
            coalesce(c.keyword, p.keyword) as keyword,
            coalesce(c.current_count, 0) as current_count,
            coalesce(p.prior_count, 0) as prior_count,
            (coalesce(c.current_count, 0) - coalesce(p.prior_count, 0))::double / (coalesce(p.prior_count, 0) + 1.0) as velocity
        FROM current_period c
        FULL OUTER JOIN prior_period p ON c.keyword = p.keyword
    """)
    
    # C. Future Trend Predictions
    # For the top keywords, fit a line on the last 15 days of counts and predict the next 5 days
    print("Running forecasting models for trending keywords...")
    top_keywords = [r[0] for r in con.execute("SELECT keyword FROM keyword_velocity ORDER BY current_count DESC LIMIT 20").fetchall()]
    
    prediction_rows = []
    all_dates = sorted([r[0] for r in con.execute("SELECT DISTINCT created_date FROM keyword_mentions").fetchall()])
    
    for kw in top_keywords:
        # Get historical daily counts
        hist_df = con.execute(f"""
            SELECT created_date, COUNT(*) as cnt 
            FROM keyword_mentions 
            WHERE keyword = '{kw}' 
            GROUP BY created_date 
            ORDER BY created_date
        """).fetch_df()
        
        # Merge with all dates to ensure we fill zeros
        full_hist = pd.DataFrame({"created_date": all_dates})
        full_hist = full_hist.merge(hist_df, on="created_date", how="left").fillna(0)
        counts = full_hist["cnt"].tolist()
        
        # Forecast 5 days out
        forecasted = forecast_trend(counts, forecast_days=5)
        
        # Save historical count points
        for i, row in full_hist.iterrows():
            prediction_rows.append({
                "keyword": kw,
                "date": row["created_date"],
                "count": float(row["cnt"]),
                "is_forecast": False
            })
            
        # Save forecasted count points
        last_dt = datetime.strptime(all_dates[-1], "%Y-%m-%d")
        for i, val in enumerate(forecasted):
            f_date = (last_dt + timedelta(days=i+1)).strftime("%Y-%m-%d")
            prediction_rows.append({
                "keyword": kw,
                "date": f_date,
                "count": val,
                "is_forecast": True
            })
            
    df_predictions = pd.DataFrame(prediction_rows)
    con.execute("CREATE OR REPLACE TABLE trend_predictions AS SELECT * FROM df_predictions")
    
    con.close()
    print("--- ETL Pipeline Completed Successfully! Database: data/trends.db ---")

if __name__ == "__main__":
    run_etl_pipeline()
