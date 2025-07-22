# nltk_setup.py

import nltk
import ssl
import os

# Define a custom NLTK data path within the project's root directory
# This makes the NLTK data part of your deployed application
NLTK_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.nltk_data')

# Create the directory if it doesn't exist
if not os.path.exists(NLTK_DATA_DIR):
    print(f"Creating NLTK data directory: {NLTK_DATA_DIR}")
    os.makedirs(NLTK_DATA_DIR)

# Add this path to NLTK's search paths
# This tells NLTK where to look for data files
if NLTK_DATA_DIR not in nltk.data.path:
    nltk.data.path.append(NLTK_DATA_DIR)
    print(f"Added {NLTK_DATA_DIR} to NLTK data search paths: {nltk.data.path}")
else:
    print(f"{NLTK_DATA_DIR} already in NLTK data search paths.")


# Handle potential SSL certificate issues during download (as seen before)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass # Not needed on all Python versions
else:
    ssl._create_default_https_context = _create_unverified_https_context

print(f"Starting NLTK data download to: {NLTK_DATA_DIR}")

# Download 'punkt' tokenizer data
print("Attempting to download 'punkt' tokenizer data...")
try:
    # download_dir specifies where to save the data
    # quiet=False ensures we see download progress/errors in logs
    nltk.download('punkt', download_dir=NLTK_DATA_DIR, quiet=False)
    print("'punkt' download successful.")
except Exception as e:
    print(f"Error downloading 'punkt': {e}")
    # Exit with an error code if critical download fails, to stop deploy
    exit(1) # This will cause the Render build to fail explicitly if download fails

# Download 'stopwords' data
print("Attempting to download 'stopwords' data...")
try:
    nltk.download('stopwords', download_dir=NLTK_DATA_DIR, quiet=False)
    print("'stopwords' download successful.")
except Exception as e:
    print(f"Error downloading 'stopwords': {e}")
    exit(1) # Exit if critical download fails

print("NLTK data setup process complete.")
