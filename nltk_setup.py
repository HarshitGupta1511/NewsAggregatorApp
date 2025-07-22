# nltk_setup.py

import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

print("Downloading NLTK 'punkt' tokenizer data...")
nltk.download('punkt', quiet=True)
print("Downloading NLTK 'stopwords' data...")
nltk.download('stopwords', quiet=True)
print("NLTK data download complete.")