# news_fetcher.py

import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re # For cleaning text

# NLTK imports for summarization
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from collections import defaultdict
from heapq import nlargest # For selecting top sentences

# --- Summarization Function ---
def summarize_text(text, num_sentences=3):
    if not text or len(text.strip()) < 50: # Basic check for very short or empty text
        return text.strip() if text else "Not enough content to summarize."

    # Clean the text (remove non-alphanumeric, extra spaces)
    # Convert to lowercase
    formatted_text = re.sub('[^a-zA-Z]', ' ', text)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)
    formatted_text = formatted_text.lower()

    # Tokenize sentences and words
    sentences = sent_tokenize(text) # Use original text for sentence tokenization
    words = word_tokenize(formatted_text)

    # Get stop words
    try:
        stop_words = set(stopwords.words('english'))
    except LookupError:
        print("NLTK 'stopwords' not found. Please run 'python -m nltk.downloader stopwords'")
        stop_words = set() # Fallback to empty set

    # Calculate word frequencies (excluding stopwords)
    word_frequencies = defaultdict(int)
    for word in words:
        if word not in stop_words:
            word_frequencies[word] += 1

    if not word_frequencies: # Handle case where no meaningful words are found
        # If no significant words after stopwords removal, return the first sentence or a default message
        return sentences[0] if sentences else "Could not generate summary."

    # Calculate weighted frequencies (relative to max frequency)
    maximum_frequency = max(word_frequencies.values())
    for word in word_frequencies:
        word_frequencies[word] = (word_frequencies[word] / maximum_frequency)

    # Calculate sentence scores based on word frequencies
    sentence_scores = defaultdict(int)
    for i, sentence in enumerate(sentences):
        for word in word_tokenize(sentence.lower()): # Tokenize sentence words for scoring
            if word in word_frequencies:
                sentence_scores[i] += word_frequencies[word]

    # Select top N sentences for summary
    summarized_sentences = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)

    # Sort sentences by their original order to maintain coherence
    final_summary_sentences = [sentences[i] for i in sorted(summarized_sentences)]

    return " ".join(final_summary_sentences)

# --- End Summarization Function ---


# --- News Fetching Function ---
# news_fetcher.py (modification only for the content extraction block within fetch_rss_news)

# ... (existing imports and summarize_text function) ...

def fetch_rss_news(rss_url, num_articles=5):
    articles = [] # Ensure this is at the very top of fetch_rss_news

    try:
        feed = feedparser.parse(rss_url)

        # Keep these debug prints for now, useful for verifying feed structure
        # print(f"DEBUG: Raw feed object type: {type(feed)}")
        # print(f"DEBUG: Raw feed object content: {feed}")

        if not feed.entries:
            feed_status = getattr(feed, 'status', 'N/A')
            feed_bozo = getattr(feed, 'bozo', 'N/A')
            feed_bozo_exception = getattr(feed, 'bozo_exception', 'N/A')
            print(f"DEBUG: feedparser returned no entries for {rss_url}.")
            print(f"       Status: {feed_status}, Bozo: {feed_bozo}, Error: {feed_bozo_exception}")
            return []

        for entry in feed.entries[:num_articles]:
            article = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.published if hasattr(entry, 'published') else 'N/A',
                'summary': entry.summary if hasattr(entry, 'summary') else 'No summary available.',
                'full_content': '',
                'generated_summary': ''
            }

            full_article_text = ""
            try:
                response = requests.get(entry.link, timeout=7)
                response.raise_for_status()

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # --- IMPROVED CONTENT EXTRACTION LOGIC (NPR specific refinement) ---
                    article_container = soup.find('article') or \
                                        soup.find('div', class_='storytext') or \
                                        soup.find('div', class_='story-body') or \
                                        soup.find('div', id='storytext') # Added common NPR id

                    if article_container:
                        # Remove scripts, styles, figures, blockquotes, lists, and specific caption containers first
                        for unwanted_tag_parent in article_container.find_all(["script", "style", "figure", "img", "blockquote", "aside", "ul", "ol", "div", "span"], class_=re.compile(r'media-caption|credit|byline|promo|share|social|tags|related-content|skip-link|audio-module|play-button|header|footer|meta|timestamp')):
                            unwanted_tag_parent.extract() # Remove entire sections that are often boilerplate

                        # Now find actual paragraphs or text-blocks
                        paragraphs = article_container.find_all('p') or \
                                     article_container.find_all('div', class_='text-block')

                        extracted_lines = []
                        for p in paragraphs:
                            # Clean within paragraph itself (e.g. nested spans for copyright)
                            for unwanted_in_p in p(["script", "style", "a.media-caption", "span.media-caption__text", "span.credit"]):
                                unwanted_in_p.extract()
                            line = p.get_text(strip=True)
                            if line and len(line) > 20: # Only add non-empty lines, and filter very short ones
                                extracted_lines.append(line)

                        full_article_text = "\n".join(extracted_lines)

                        # General cleaning: Consolidate newlines and spaces
                        full_article_text = re.sub(r'(\n\s*)+\n', '\n', full_article_text).strip()
                        full_article_text = re.sub(r'\s+', ' ', full_article_text).strip()

                        # --- AGGRESSIVE REGEX CLEANING FOR NPR'S PERSISTENT BOILERPLATE ---
                        # Remove common, non-article specific phrases that might still appear (NPR specific)
                        full_article_text = re.sub(r'(?i)toggle caption', '', full_article_text).strip()
                        full_article_text = re.sub(r'(?i)download audio', '', full_article_text).strip()
                        full_article_text = re.sub(r'(?i)listen to the story', '', full_article_text).strip()
                        full_article_text = re.sub(r'(?i)read more', '', full_article_text).strip()
                        full_article_text = re.sub(r'This story was produced by\s*.*', '', full_article_text).strip()
                        full_article_text = re.sub(r'(\s*\(AP\)\s*|\s*\(Reuters\)\s*|\s*\(NPR\)\s*|\s*\(CNN\)\s*|\s*\(New York Times\)\s*)', '', full_article_text).strip()
                        full_article_text = re.sub(r'(\s*NPR is a\s*.*)', '', full_article_text).strip()
                        full_article_text = re.sub(r'(\s*Copyright\s*\d{4}\s*NPR)', '', full_article_text).strip()

                        # Very specific patterns for image/caption remnants
                        full_article_text = re.sub(r'^[A-Z][a-z]+ [A-Z][a-z]+/(Getty|AP|NPR) Images(hide caption)?\s*', '', full_article_text).strip() # Match "Firstname Lastname/Getty Imageshide caption"
                        full_article_text = re.sub(r'^(Getty|AP|NPR) Images(hide caption)?\s*', '', full_article_text).strip() # Match "Getty Imageshide caption"
                        full_article_text = re.sub(r'^(.*?)/(Associated Press|Reuters|AFP|NPR)(hide caption)?\s*', '', full_article_text).strip() # Match anything/WireServicehide caption
                        full_article_text = re.sub(r'^(.*?)\s*hide caption\s*', '', full_article_text, flags=re.IGNORECASE).strip() # Catch lingering "hide caption"
                        full_article_text = re.sub(r'^(Credit|Source|Photo by|AP Photo|REUTERS/|NPR photo|Image caption):?\s*.*', '', full_article_text, flags=re.IGNORECASE).strip() # Catch explicit credit lines at start
                        full_article_text = re.sub(r'^(Image|Photo|Video)\s+via\s+.*', '', full_article_text, flags=re.IGNORECASE).strip() # Catch "Image via..."
                        full_article_text = re.sub(r'\b(embed|enlarge|audio|video|picture|photo|illustration|graphic)\b', '', full_article_text, flags=re.IGNORECASE).strip() # Remove common media words if alone
                        full_article_text = re.sub(r'\s{2,}', ' ', full_article_text).strip() # Clean up any double spaces from removals
                        # --- END AGGRESSIVE REGEX CLEANING ---


                        # Limit input length to summarizer
                        if len(full_article_text) > 5000:
                            full_article_text = full_article_text[:5000]

                        if not full_article_text.strip() or len(full_article_text.strip()) < 50: # Check again after aggressive cleaning
                             article['full_content'] = "Could not extract sufficient main article content after aggressive cleaning."
                             full_article_text = ""
                        else:
                            article['full_content'] = full_article_text[:497] + '...' if len(full_article_text) > 497 else full_article_text

                    else:
                        article['full_content'] = "Could not identify primary article content area."
                        full_article_text = ""

            except requests.exceptions.HTTPError as errh:
                article['full_content'] = f"HTTP Error: {errh}"
                print(f"DEBUG: HTTP error for {entry.link}: {errh}")
            except requests.exceptions.ConnectionError as errc:
                article['full_content'] = f"Error Connecting: {errc}"
                print(f"DEBUG: Connection error for {entry.link}: {errc}")
            except requests.exceptions.Timeout as errt:
                article['full_content'] = f"Timeout Error: {errt}"
                print(f"DEBUG: Timeout error for {entry.link}: {errt}")
            except requests.exceptions.RequestException as err:
                article['full_content'] = f"Something went wrong with request: {err}"
                print(f"DEBUG: Request error for {entry.link}: {err}")
            except Exception as e:
                article['full_content'] = f"An unexpected error occurred during content fetching: {e}"
                print(f"DEBUG: Unexpected error fetching content for {entry.link}: {e}")

            # Generate summary using the fetched full content
            if full_article_text and len(full_article_text) > 100 and full_article_text not in ["Could not extract sufficient main article content after cleaning.", "Could not identify primary article content area."]:
                article['generated_summary'] = summarize_text(full_article_text, num_sentences=3)
            else:
                article['generated_summary'] = "Summary not available (full content too short or not extracted cleanly)."

            articles.append(article)
        return articles
    except Exception as e:
        print(f"ERROR in fetch_rss_news for {rss_url}: {type(e).__name__} - {e}")
        return []

# ... (rest of the file) ...

# Example Usage (for testing the module directly)
if __name__ == '__main__':
    # IMPORTANT: Ensure app.py also uses this NPR RSS URL
    test_rss_url = "https://www.npr.org/rss/rss.php?id=1001"
    news_items = fetch_rss_news(test_rss_url, num_articles=3)
    if news_items:
        print(f"\n--- Latest News from {test_rss_url} ---")
        for i, item in enumerate(news_items):
            print(f"\nArticle {i+1}:")
            print(f"  Title: {item['title']}")
            print(f"  Link: {item['link']}")
            print(f"  Published: {item['published']}")
            print(f"  Original Summary: {item['summary'][:150]}...")
            print(f"  Full Content (excerpt): {item['full_content'][:200]}...") # Truncated for display
            print(f"  Generated Summary: {item['generated_summary'][:200]}...") # Truncated for display
    else:
        print("No news fetched or an error occurred.")
