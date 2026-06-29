import os
import csv
import random
from datetime import datetime, timedelta

# Define the directory path for raw data
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')

# Sample data pools for topics
TOPICS = {
    "AI & ChatGPT": {
        "keywords": ["AI", "ChatGPT", "LLM", "artificial intelligence", "machine learning", "OpenAI"],
        "sentiment": {
            "positive": [
                "ChatGPT is absolutely changing the way I code! Truly amazing.",
                "AI is the future of productivity. The automation tools are incredible.",
                "Incredible breakthroughs in machine learning recently. Exciting times!",
                "Using LLMs for research has saved me hours of work.",
                "The new AI models are showing remarkable reasoning capabilities."
            ],
            "neutral": [
                "OpenAI released an update to ChatGPT today.",
                "Looking into how artificial intelligence is regulated in Europe.",
                "Here is a comparison of different machine learning frameworks.",
                "How does an LLM handle context windows? Let's discuss.",
                "AI developments continue to dominate tech news."
            ],
            "negative": [
                "Worried about the job losses due to ChatGPT and AI tools.",
                "AI hallucinations are making it hard to trust these models.",
                "The carbon footprint of training massive LLMs is concerning.",
                "Another generic AI startup that doesn't solve a real problem.",
                "AI copyright lawsuits are piling up. It's a legal mess."
            ]
        },
        "subreddits": ["technology", "science"],
        "trend_curve": lambda day: 10 + day * 1.5 + random.randint(-5, 5)  # Steady growth
    },
    "Cryptocurrency & Web3": {
        "keywords": ["crypto", "bitcoin", "ethereum", "web3", "blockchain", "solana"],
        "sentiment": {
            "positive": [
                "Bitcoin is rallying again! To the moon!",
                "Ethereum gas fees are finally low, time to interact with smart contracts.",
                "Web3 is rebuilding the internet to be decentralized and user-owned.",
                "Blockchain technology has so many use cases beyond currency.",
                "Bull market is back! Crypto portfolios are looking green."
            ],
            "neutral": [
                "Bitcoin price holds steady at current support levels.",
                "Solana network completed a scheduled upgrade today.",
                "A discussion on the consensus mechanisms of modern blockchains.",
                "Regulatory framework for crypto assets is being debated in Congress.",
                "What is your favorite hardware wallet for storing crypto?"
            ],
            "negative": [
                "Another crypto exchange got hacked. When will we learn?",
                "Web3 is mostly just speculation and useless NFTs.",
                "Lost gas fees on a failed Ethereum transaction, so annoying.",
                "Bitcoin's energy consumption is terrible for the environment.",
                "Crypto regulation is getting too aggressive, killing innovation."
            ]
        },
        "subreddits": ["finance", "technology"],
        "trend_curve": lambda day: 20 + 15 * (1 if 10 <= day <= 14 else 0) + random.randint(-8, 8)  # Volatile spike
    },
    "Market Inflation & Recession": {
        "keywords": ["inflation", "recession", "interest rates", "stock market", "Federal Reserve", "layoffs"],
        "sentiment": {
            "positive": [
                "Stock market is hitting new highs today! Great recovery.",
                "Federal Reserve might cut interest rates soon, index funds are rising.",
                "Layoffs are tough, but companies are becoming leaner and more efficient.",
                "Inflation numbers came in lower than expected, good sign for the economy.",
                "Buying the dip in the stock market pays off in the long run."
            ],
            "neutral": [
                "Federal Reserve scheduled to announce interest rate decision tomorrow.",
                "Analyzing inflation data from the last quarter.",
                "A look at historical market performance during rate cycles.",
                "Corporate earnings report season begins next week.",
                "How does inflation affect long-term treasury yields?"
            ],
            "negative": [
                "Inflation is making groceries and rent unaffordable. Hard times.",
                "More tech layoffs announced today. The job market is brutal.",
                "A recession feels inevitable at this rate. Interest rates are too high.",
                "Stock market is crashing! Portfolios are down 20%.",
                "Companies are freezing hiring. This economy is scary."
            ]
        },
        "subreddits": ["finance", "news"],
        "trend_curve": lambda day: 5 + (80 if 15 <= day <= 18 else 0) + random.randint(-4, 4)  # Huge crash spike on days 15-18
    },
    "Remote Work & WFH": {
        "keywords": ["remote work", "WFH", "work from home", "zoom", "hybrid work", "return to office"],
        "sentiment": {
            "positive": [
                "Remote work has improved my mental health and work-life balance so much.",
                "No more daily commute! WFH is the best benefit a company can offer.",
                "Setup my new home office, feeling super productive today.",
                "Hybrid work gives the perfect balance of collaboration and flexibility.",
                "Remote work allows me to spend more time with my family."
            ],
            "neutral": [
                "A survey on remote work preferences among software engineers.",
                "Comparing Zoom, Teams, and Slack for remote team collaboration.",
                "Many companies are adopting hybrid work policies.",
                "Discussion about home office tax deductions.",
                "How do remote teams build culture?"
            ],
            "negative": [
                "Return to office mandates are ruining employee morale.",
                "Remote work makes it harder to separate personal life from working hours.",
                "Zoom fatigue is real. Too many meetings that could have been emails.",
                "I miss the office interactions and casual coffee chats with coworkers.",
                "WFH is lonely. I feel disconnected from my team."
            ]
        },
        "subreddits": ["technology", "news"],
        "trend_curve": lambda day: 15 + random.randint(-3, 3)  # Stable baseline
    },
    "Quantum Computing": {
        "keywords": ["quantum computing", "quantum", "physics", "qubits", "supercomputing"],
        "sentiment": {
            "positive": [
                "Excited about the progress in quantum computing and error correction!",
                "Quantum computers will solve chemistry problems that are impossible today.",
                "Superconducting qubits are reaching higher coherence times. Amazing physics.",
                "This quantum breakthrough could revolutionize cryptography.",
                "A fantastic lecture on quantum algorithms and complexity."
            ],
            "neutral": [
                "A new paper on quantum supremacy was published in Nature.",
                "What is the difference between topological and spin qubits?",
                "Tech giants are investing heavily in quantum research labs.",
                "A basic explanation of quantum superposition and entanglement.",
                "Academic research on quantum error correction continues."
            ],
            "negative": [
                "Quantum computing is still decades away from solving practical problems.",
                "A lot of hype in the quantum computing sector with little output.",
                "Decoherence is such a hard engineering problem, we might never solve it.",
                "Quantum computers threaten modern encryption. This is dangerous.",
                "So much quantum buzzword salad in tech marketing nowadays."
            ]
        },
        "subreddits": ["science", "technology"],
        "trend_curve": lambda day: 2 + day * 0.5 + random.randint(-1, 2)  # Low volume but steady upward trend (emerging)
    },
    "Climate Change": {
        "keywords": ["climate change", "global warming", "renewable energy", "carbon emissions", "solar power"],
        "sentiment": {
            "positive": [
                "Solar and wind power are now cheaper than fossil fuels in most places! Excellent.",
                "Electric vehicle adoption is accelerating worldwide, great news for climate.",
                "Renewable energy capacity broke records this year.",
                "Reforestation projects are showing positive ecological impacts.",
                "New carbon capture technologies are showing promise."
            ],
            "neutral": [
                "UN climate summit scheduled for next month to discuss emissions targets.",
                "Analyzing global temperature anomalies over the last decade.",
                "A report on the share of renewable energy in the national grid.",
                "Scientific study models the melting rate of polar ice sheets.",
                "How do carbon tax credits work?"
            ],
            "negative": [
                "Global warming is accelerating. Extreme weather events are everywhere.",
                "Carbon emissions hit another record high. We are not doing enough.",
                "Rising sea levels are threatening coastal communities.",
                "The political inaction on climate change is deeply frustrating.",
                "Microplastics and pollution are destroying marine ecosystems."
            ]
        },
        "subreddits": ["science", "news"],
        "trend_curve": lambda day: 12 + random.randint(-4, 4)  # Stable baseline
    }
}

USERNAMES = ["tech_guru", "finance_broker", "science_guy", "code_monkey", "crypto_whale", 
             "data_wizard", "eco_warrior", "macro_trader", "curious_mind", "pixel_perfect",
             "spark_dev", "duckdb_fan", "reddit_user_1", "tweet_bot", "news_anchor"]

def generate_data(num_days=30):
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    start_date = datetime.now() - timedelta(days=num_days)
    
    tweets = []
    reddit_posts = []
    reddit_comments = []
    
    tweet_id_counter = 100000
    post_id_counter = 500000
    comment_id_counter = 900000
    
    for d in range(num_days):
        current_date = start_date + timedelta(days=d)
        
        for topic_name, topic_info in TOPICS.items():
            # Determine volume for this topic on this day based on the trend curve
            volume = int(topic_info["trend_curve"](d))
            volume = max(2, volume)  # Ensure at least some data
            
            for _ in range(volume):
                # Determine sentiment category for this item
                # Inflation spike is negative, crypto spike is volatile, etc.
                if topic_name == "Market Inflation & Recession" and 15 <= d <= 18:
                    sent_cat = random.choices(["positive", "neutral", "negative"], weights=[5, 15, 80])[0]
                elif topic_name == "Cryptocurrency & Web3" and 10 <= d <= 14:
                    sent_cat = random.choices(["positive", "neutral", "negative"], weights=[50, 10, 40])[0]
                else:
                    sent_cat = random.choices(["positive", "neutral", "negative"], weights=[35, 45, 20])[0]
                
                text = random.choice(topic_info["sentiment"][sent_cat])
                username = random.choice(USERNAMES)
                
                # Add random variations to text to simulate realistic data
                keyword = random.choice(topic_info["keywords"])
                if random.random() > 0.5:
                    # Sometimes append hashtag
                    text += f" #{keyword.replace(' ', '')}"
                
                # Generate timestamp with random hour/minute
                item_time = current_date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                time_str = item_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # --- Generate Tweet ---
                likes = random.randint(0, 500)
                # Some tweets go viral
                if random.random() > 0.95:
                    likes = random.randint(1000, 15000)
                retweets = int(likes * random.uniform(0.1, 0.4))
                
                tweets.append({
                    "tweet_id": tweet_id_counter,
                    "username": username,
                    "text": text,
                    "created_at": time_str,
                    "retweets": retweets,
                    "likes": likes
                })
                tweet_id_counter += 1
                
                # --- Generate Reddit Post (about 50% ratio of posts compared to tweets) ---
                if random.random() > 0.5:
                    subreddit = random.choice(topic_info["subreddits"])
                    score = random.randint(1, 1000)
                    if random.random() > 0.95:
                        score = random.randint(2000, 25000)
                    num_comments = int(score * random.uniform(0.05, 0.2)) + 1
                    
                    title = f"Discussion on {keyword}: {text[:40]}..."
                    selftext = text + " What are your thoughts on this? Let me know below."
                    
                    post_id = f"t3_{post_id_counter}"
                    reddit_posts.append({
                        "post_id": post_id,
                        "subreddit": subreddit,
                        "title": title,
                        "selftext": selftext,
                        "author": username,
                        "score": score,
                        "num_comments": num_comments,
                        "created_utc": time_str
                    })
                    post_id_counter += 1
                    
                    # --- Generate Comments for this post ---
                    # Number of comments to generate is smaller than num_comments to keep dataset size reasonable
                    comments_to_gen = min(random.randint(1, 5), num_comments)
                    for _ in range(comments_to_gen):
                        c_sent_cat = random.choices(["positive", "neutral", "negative"], weights=[30, 40, 30])[0]
                        c_text = random.choice(topic_info["sentiment"][c_sent_cat])
                        c_time = item_time + timedelta(minutes=random.randint(5, 300))
                        c_time_str = c_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        reddit_comments.append({
                            "comment_id": f"t1_{comment_id_counter}",
                            "post_id": post_id,
                            "body": c_text,
                            "author": random.choice(USERNAMES),
                            "score": random.randint(-5, 200),
                            "created_utc": c_time_str
                        })
                        comment_id_counter += 1
                        
    # Write to CSV files
    tweets_file = os.path.join(RAW_DATA_DIR, "tweets.csv")
    with open(tweets_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tweet_id", "username", "text", "created_at", "retweets", "likes"])
        writer.writeheader()
        writer.writerows(tweets)
        
    posts_file = os.path.join(RAW_DATA_DIR, "reddit_posts.csv")
    with open(posts_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["post_id", "subreddit", "title", "selftext", "author", "score", "num_comments", "created_utc"])
        writer.writeheader()
        writer.writerows(reddit_posts)
        
    comments_file = os.path.join(RAW_DATA_DIR, "reddit_comments.csv")
    with open(comments_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["comment_id", "post_id", "body", "author", "score", "created_utc"])
        writer.writeheader()
        writer.writerows(reddit_comments)
        
    print(f"Generated {len(tweets)} tweets -> {tweets_file}")
    print(f"Generated {len(reddit_posts)} Reddit posts -> {posts_file}")
    print(f"Generated {len(reddit_comments)} Reddit comments -> {comments_file}")

if __name__ == "__main__":
    generate_data()
