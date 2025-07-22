# app.py

from flask import Flask, render_template, request, redirect, url_for, session
from news_fetcher import fetch_rss_news
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Define a default list of RSS feeds. This will be used on first load.
DEFAULT_RSS_FEEDS = [
    "https://www.npr.org/rss/rss.php?id=1001" # NPR Top Stories
    # "http://feeds.bbci.co.uk/news/rss.xml" ,
    # "http://sports.espn.go.com/espn/rss/news"
    # BBC News Top Stories (still challenging to scrape full content, but we'll try)
    # Add more default feeds here if you like, e.g., for sports:
    # "http://sports.espn.go.com/espn/rss/news" # ESPN News (check if this URL is still active/valid)
]

@app.route('/')
def home():
    # Retrieve user preferences from the session, or use defaults
    user_rss_feeds = session.get('rss_feeds', DEFAULT_RSS_FEEDS) # Get list of feeds
    user_keywords = session.get('keywords', '')
    user_exclude_keywords = session.get('exclude_keywords', '')
    user_num_articles = session.get('num_articles', 10)

    # Convert num_articles to integer, handle potential errors
    try:
        user_num_articles = int(user_num_articles)
        if not (1 <= user_num_articles <= 50): # Cap between 1 and 50
            user_num_articles = 10
    except (ValueError, TypeError):
        user_num_articles = 10

    # --- Fetch news from MULTIPLE sources ---
    all_raw_articles = []
    for feed_url in user_rss_feeds:
        # Fetch more articles per feed to allow for better filtering across combined sources
        articles_from_feed = fetch_rss_news(feed_url, num_articles=25) # Fetch 25 from each
        all_raw_articles.extend(articles_from_feed) # Add to the master list

    # Apply filtering based on user preferences
    filtered_articles = []
    keywords_list = [k.strip().lower() for k in user_keywords.split(',') if k.strip()]
    exclude_keywords_list = [k.strip().lower() for k in user_exclude_keywords.split(',') if k.strip()]

    for article in all_raw_articles: # Iterate through ALL fetched articles
        # Ensure necessary keys exist before accessing, provide defaults if not
        title_lower = article.get('title', '').lower()
        summary_lower = article.get('summary', '').lower()
        full_content_lower = article.get('full_content', '').lower()
        generated_summary_lower = article.get('generated_summary', '').lower()

        # Check for inclusion keywords (if any provided)
        if keywords_list:
            if not any(kw in title_lower or kw in summary_lower or kw in full_content_lower or kw in generated_summary_lower for kw in keywords_list):
                continue # Skip this article if no inclusion keyword is found

        # Check for exclusion keywords (if any provided)
        if exclude_keywords_list:
            if any(ex_kw in title_lower or ex_kw in summary_lower or ex_kw in full_content_lower or ex_kw in generated_summary_lower for ex_kw in exclude_keywords_list):
                continue # Skip this article if an exclusion keyword is found

        filtered_articles.append(article)

    # Limit the number of articles displayed (from the combined & filtered list)
    articles_to_display = filtered_articles[:user_num_articles]

    # Render the index.html template and pass the articles and session data
    return render_template(
        'index.html',
        articles=articles_to_display,
        session=session # Pass the entire session object to the template for default values
    )

@app.route('/customize', methods=['POST'])
def customize():
    # Get data from the form submission
    # For rss_feeds, it comes as a single string with newlines, split it into a list
    rss_feeds_raw = request.form.get('rss_feeds', '').strip()
    rss_feeds_list = [url.strip() for url in rss_feeds_raw.split('\n') if url.strip()]

    keywords = request.form.get('keywords', '').strip()
    exclude_keywords = request.form.get('exclude_keywords', '').strip()
    num_articles = request.form.get('num_articles', '10').strip()

    # Store preferences in the session
    session['rss_feeds'] = rss_feeds_list # Store as a list
    session['keywords'] = keywords
    session['exclude_keywords'] = exclude_keywords
    session['num_articles'] = num_articles

    # Redirect back to the home page to display news with new preferences
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)