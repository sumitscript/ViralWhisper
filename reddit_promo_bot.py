import praw
import csv
import time
from datetime import datetime
import httpx
from string import Template
import os
import json
import logging
import sys
import random
from configparser import ConfigParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reddit_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RedditBot")

# CONFIG - Create a config.ini file with these values or replace with your actual credentials
def create_default_config():
    """Create default config.ini file if it doesn't exist"""
    if not os.path.exists('config.ini'):
        config = ConfigParser()
        config['reddit'] = {
            'client_id': 'YOUR_CLIENT_ID',
            'client_secret': 'YOUR_CLIENT_SECRET',
            'username': 'YOUR_REDDIT_USERNAME',
            'password': 'YOUR_REDDIT_PASSWORD',
            'user_agent': 'BoardGamePromotionBot/1.0 by YOUR_USERNAME'
        }
        config['ollama'] = {
            'base_url': 'http://localhost:11434'
        }
        with open('config.ini', 'w') as f:
            config.write(f)
        logger.info("Created default config.ini file. Please edit with your credentials.")
        return False
    return True

# Load configuration
def load_config():
    """Load configuration from config.ini"""
    if not create_default_config():
        sys.exit(1)
        
    config = ConfigParser()
    config.read('config.ini')
    
    # Check if configuration has been updated from defaults
    if config['reddit']['client_id'] == 'YOUR_CLIENT_ID':
        logger.error("Please edit config.ini with your Reddit API credentials")
        sys.exit(1)
        
    return config

# Ollama configuration
def check_ollama_status(base_url):
    """Check if Ollama service is running."""
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            logger.info(f"Ollama is running. Available models: {[m['name'] for m in models]}")
            return True
        logger.error(f"Ollama status check failed with status code: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Ollama service check failed: {e}")
        return False

# Template for generating comment and promotional line for Kickstarter Game
GAME_PROMO_TEMPLATE = Template(
    """Based on the following Reddit post about Kickstarter/crowdfunding/games: 

Title: "$post_title"
Content: "$post_text"
    
Generate a relevant, conversational comment (30-70 words) that engages with the post's content in a supportive, inquisitive way. The tone should be helpful and community-oriented.
    
Also, provide a subtle promotional line (15-25 words) about an upcoming card game called "Hand Cricket Showdown" that's inspired by cricket but played with cards. It's a 2-player strategic game that will be coming to Kickstarter soon. Make the promo feel natural and not forced.
    
Return the response in the format:
Comment: [Your comment here]
Promo: [Your promotional line here]"""
)

def authenticate_reddit(config):
    """Authenticate with Reddit API using PRAW."""
    try:
        reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            username=config['reddit']['username'],
            password=config['reddit']['password'],
            user_agent=config['reddit']['user_agent']
        )
        
        # Verify authentication
        username = reddit.user.me().name
        logger.info(f"Reddit API authentication successful. Logged in as: {username}")
        return reddit
    except Exception as e:
        logger.error(f"Reddit API authentication failed: {e}")
        return None

def get_relevant_posts(reddit, limit=5):
    """Get relevant posts from selected subreddits."""
    relevant_subreddits = [
        "boardgames", "tabletopgames", "crowdfunding", 
        "kickstarter", "boardgamedesign", "indiegames"
    ]
    
    # Choose a random subreddit from the list to avoid spamming any single one
    subreddit_name = random.choice(relevant_subreddits)
    logger.info(f"Searching in r/{subreddit_name}")
    
    # Get new posts from the selected subreddit
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    
    try:
        for post in subreddit.new(limit=limit):
            # Filter posts that mention relevant keywords
            if is_relevant_post(post):
                posts.append(post)
                logger.info(f"Found relevant post: {post.title}")
    except Exception as e:
        logger.error(f"Error retrieving posts from r/{subreddit_name}: {e}")
    
    # If we didn't find enough posts, try another subreddit
    if len(posts) == 0 and len(relevant_subreddits) > 1:
        relevant_subreddits.remove(subreddit_name)
        subreddit_name = random.choice(relevant_subreddits)
        logger.info(f"No relevant posts found, trying r/{subreddit_name}")
        
        try:
            subreddit = reddit.subreddit(subreddit_name)
            for post in subreddit.new(limit=limit):
                if is_relevant_post(post):
                    posts.append(post)
                    logger.info(f"Found relevant post: {post.title}")
        except Exception as e:
            logger.error(f"Error retrieving posts from r/{subreddit_name}: {e}")
    
    return posts

def is_relevant_post(post):
    """Check if a post is relevant based on keywords."""
    keywords = [
        "kickstarter", "crowdfunding", "board game", "card game", "tabletop", 
        "funding", "campaign", "stretch goal", "back this", "project", 
        "indie game", "launch", "creator"
    ]
    
    # Skip posts that are already very popular
    if post.score > 100:
        return False
    
    # Skip posts that we've already commented on
    post.comments.replace_more(limit=0)
    for comment in post.comments.list():
        if comment.author and comment.author.name == post.reddit.user.me().name:
            logger.info(f"Already commented on post: {post.title}")
            return False
    
    # Check title and selftext for keywords
    title_lower = post.title.lower()
    selftext_lower = post.selftext.lower() if hasattr(post, 'selftext') else ""
    
    for keyword in keywords:
        if keyword.lower() in title_lower or keyword.lower() in selftext_lower:
            return True
    
    return False

def generate_comment_and_promo(post_title, post_text, ollama_base_url):
    """Generate comment and promotional line using Ollama for Kickstarter game."""
    try:
        # Check if models are available
        try:
            response = httpx.get(f"{ollama_base_url}/api/tags", timeout=5)
            models = [m["name"] for m in response.json().get("models", [])]
            
            # Use available model (preferably deepseek-r1)
            model = "deepseek-r1" if "deepseek-r1" in models else models[0] if models else None
            
            if not model:
                logger.error("No Ollama models available")
                # Fallback response
                return generate_fallback_response()
                
            logger.info(f"Using Ollama model: {model}")
        except Exception as e:
            logger.error(f"Error checking Ollama models: {e}")
            return generate_fallback_response()
        
        prompt = GAME_PROMO_TEMPLATE.substitute(post_title=post_title, post_text=post_text)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        response = httpx.post(
            f"{ollama_base_url}/api/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return generate_fallback_response()
            
        result = response.json().get("response", "").strip()
        
        # Parse response to extract comment and promo
        lines = result.split("\n")
        comment = next((line[8:].strip() for line in lines if line.startswith("Comment:")), "")
        promo = next((line[6:].strip() for line in lines if line.startswith("Promo:")), "")
        
        # If parsing failed, use fallback
        if not comment or not promo:
            return generate_fallback_response()
        
        logger.info(f"Generated comment: {comment}")
        logger.info(f"Generated promo: {promo}")
        
        # Combine comment and promo for the reddit reply
        combined_reply = f"{comment}\n\n{promo}"
        return combined_reply, promo
    except Exception as e:
        logger.error(f"Error generating comment/promo: {e}")
        return generate_fallback_response()

def generate_fallback_response():
    """Generate a fallback response when Ollama fails."""
    comments = [
        "This looks really interesting! I love seeing innovative projects in the tabletop space. What inspired you to create this?",
        "Really cool concept! The gaming community always benefits from fresh ideas like this. How long has this been in development?",
        "The artwork and concept look fantastic! As a tabletop enthusiast, I'm always excited to see new projects like this.",
        "This is exactly the kind of project that makes the board game community so special. Love seeing creators pursuing their passion!"
    ]
    
    promos = [
        "By the way, I'm working on Hand Cricket Showdown, a strategic card game inspired by cricket. Would love your thoughts sometime!",
        "Speaking of card games, our team is developing Hand Cricket Showdown, a strategic 2-player game coming to Kickstarter soon.",
        "As a fellow creator, I'm finishing up Hand Cricket Showdown - a strategic card game that brings cricket mechanics to tabletop gaming.",
        "If you're into strategic card games, we're launching Hand Cricket Showdown on Kickstarter soon - a unique cricket-inspired duel!"
    ]
    
    return f"{random.choice(comments)}\n\n{random.choice(promos)}", random.choice(promos)

def post_comment(post, comment):
    """Post a comment on a Reddit post."""
    try:
        time.sleep(2)  # Small delay to avoid rate limiting
        response = post.reply(comment)
        logger.info(f"Posted comment on '{post.title}'")
        return response
    except Exception as e:
        if "rate limit" in str(e).lower():
            logger.error(f"Rate limited by Reddit: {e}")
            wait_time = extract_wait_time(str(e)) or 600  # Default 10 minutes if can't extract
            logger.info(f"Waiting {wait_time} seconds before trying again")
            time.sleep(wait_time)
            return None
        else:
            logger.error(f"Error posting comment: {e}")
            return None

def extract_wait_time(error_message):
    """Extract wait time from Reddit rate limit error message."""
    import re
    # Try to find a number followed by "minute" or "minutes"
    minutes_match = re.search(r'(\d+) minute', error_message)
    if minutes_match:
        return int(minutes_match.group(1)) * 60
    
    # Try to find a number followed by "second" or "seconds"
    seconds_match = re.search(r'(\d+) second', error_message)
    if seconds_match:
        return int(seconds_match.group(1))
    
    return None

def ensure_csv_file_exists():
    """Make sure the CSV file exists and has headers."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "reddit_interactions.csv")
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["Timestamp", "Post ID", "Post Title", "Subreddit", "Reply", "Promotional Line"])
    return csv_path

def main():
    logger.info("Starting Reddit AI bot for Hand Cricket Showdown promotion...")
    
    # Check internet connectivity
    try:
        test_conn = httpx.get("https://www.google.com", timeout=5)
        logger.info("Internet connection is working")
    except Exception as e:
        logger.error(f"Internet connection test failed: {e}")
        logger.error("Please check your internet connection and try again")
        return
    
    # Load configuration
    config = load_config()
    
    # Check if Ollama is running
    ollama_base_url = config['ollama']['base_url']
    if not check_ollama_status(ollama_base_url):
        logger.error("Ollama service is not running. Please start Ollama and try again.")
        return
        
    # Authenticate with Reddit API
    reddit = authenticate_reddit(config)
    if not reddit:
        logger.error("Reddit authentication failed. Cannot proceed.")
        return

    # Get relevant posts
    logger.info("Searching for relevant posts about crowdfunding/board games...")
    posts = get_relevant_posts(reddit)
    
    if not posts:
        logger.info("No relevant posts found to process.")
        return
    
    logger.info(f"Found {len(posts)} relevant posts.")
    
    # Ensure CSV file exists with headers
    csv_path = ensure_csv_file_exists()

    # Open CSV file to store results
    with open(csv_path, "a", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)

        # Process each post
        for i, post in enumerate(posts, 1):
            # Add random delay between posts to appear more natural
            if i > 1:
                delay = random.randint(30, 120)
                logger.info(f"Waiting {delay} seconds before processing next post...")
                time.sleep(delay)
            
            post_title = post.title
            post_text = post.selftext if hasattr(post, 'selftext') else ""
            post_id = post.id
            subreddit = post.subreddit.display_name
            
            logger.info(f"\n[{i}/{len(posts)}] Processing post from r/{subreddit}: {post_title}")

            # Generate comment and promotional line
            reply, promo = generate_comment_and_promo(post_title, post_text, ollama_base_url)
            if not reply or not promo:
                logger.warning("Skipping post due to comment/promo generation failure.")
                continue

            # Post comment
            comment_obj = post_comment(post, reply)
            
            if comment_obj:
                # Save to CSV
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_writer.writerow([timestamp, post_id, post_title, subreddit, reply, promo])
                logger.info(f"Saved interaction for post {post_id}")
                
                # Add a longer delay after successful posting to avoid looking like a bot
                time.sleep(random.randint(60, 180))

    logger.info("\nReddit AI bot completed successfully!")

if __name__ == "__main__":
    main()
