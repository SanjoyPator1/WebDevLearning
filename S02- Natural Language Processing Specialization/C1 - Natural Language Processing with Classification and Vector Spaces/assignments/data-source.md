# Complete Data Sourcing & Preparation Guide

## For NLP Course 1 - All 4 Weeks

---

## 📋 Table of Contents

1. [Week 1 & 2: Movie Reviews Dataset](#week-1--2-movie-reviews-dataset)
2. [Week 3: Word Embeddings](#week-3-word-embeddings)
3. [Week 4: Bilingual Embeddings & Tweets](#week-4-bilingual-embeddings--tweets)
4. [Alternative Datasets](#alternative-datasets)
5. [Data Format Conversions](#data-format-conversions)
6. [Troubleshooting](#troubleshooting)

---

## Week 1 & 2: Movie Reviews Dataset

### 📥 Option 1: IMDB Movie Reviews (Recommended)

**Best for**: Weeks 1 and 2 (Logistic Regression & Naive Bayes)

#### Direct Download Links:

**1. Kaggle - IMDB Dataset of 50K Movie Reviews**

- **URL**: https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews
- **Size**: 50,000 reviews (25K train + 25K test)
- **Format**: CSV file
- **Columns**: `review`, `sentiment`
- **Labels**: `positive`, `negative`

**How to download**:

```bash
# Install kaggle CLI
pip install kaggle

# Set up Kaggle API credentials (see below)
# Download dataset
kaggle datasets download -d lakshmi25npathi/imdb-dataset-of-50k-movie-reviews

# Unzip
unzip imdb-dataset-of-50k-movie-reviews.zip
```

**2. Stanford IMDB Dataset (Original)**

- **URL**: http://ai.stanford.edu/~amaas/data/sentiment/
- **Direct Download**: http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz
- **Size**: 3.6 GB (50,000 reviews)
- **Format**: Text files in directories
- **Structure**:
  ```
  aclImdb/
  ├── train/
  │   ├── pos/     # 12,500 positive reviews
  │   └── neg/     # 12,500 negative reviews
  └── test/
      ├── pos/     # 12,500 positive reviews
      └── neg/     # 12,500 negative reviews
  ```

**How to download**:

```bash
# Download
wget http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz

# Extract
tar -xvzf aclImdb_v1.tar.gz
```

---

### 📝 Data Format & Shape

#### Raw Format (from Stanford):

```
File: train/pos/0_9.txt
Content: "Bromwell High is a cartoon comedy. It ran at the same time as some other programs about school life..."
Label: positive (from directory name)
```

#### CSV Format (from Kaggle):

```csv
review,sentiment
"Bromwell High is a cartoon comedy...",positive
"Story of a man who has...",negative
```

---

### 🔧 Converting to Required Format

#### For Week 1 & 2 Assignments:

Your code expects:

- **X**: List of review texts (strings)
- **Y**: List of labels (1 for positive, 0 for negative)

**From Kaggle CSV**:

```python
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('IMDB Dataset.csv')

# Check structure
print(df.head())
print(df['sentiment'].value_counts())

# Convert to required format
X = df['review'].tolist()  # List of strings
Y = (df['sentiment'] == 'positive').astype(int).tolist()  # 1 for positive, 0 for negative

# Verify
print(f"Total reviews: {len(X)}")
print(f"Positive: {sum(Y)}, Negative: {len(Y) - sum(Y)}")

# Split into train/test (80/20)
from sklearn.model_selection import train_test_split

X_train, X_test, Y_train, Y_test = train_test_split(
    X, Y, test_size=0.2, random_state=42, stratify=Y
)

print(f"\nTrain set: {len(X_train)} reviews")
print(f"Test set: {len(X_test)} reviews")
```

**From Stanford Directory Structure**:

```python
import os
import glob

def load_imdb_from_directories(data_dir):
    """
    Load IMDB dataset from directory structure

    Args:
        data_dir: Path to 'aclImdb' folder

    Returns:
        X_train, Y_train, X_test, Y_test
    """

    def load_reviews(base_path, sentiment):
        """Load all reviews from a directory"""
        reviews = []
        labels = []

        # Get all .txt files
        files = glob.glob(os.path.join(base_path, sentiment, '*.txt'))

        for filepath in files:
            with open(filepath, 'r', encoding='utf-8') as f:
                reviews.append(f.read())
                labels.append(1 if sentiment == 'pos' else 0)

        return reviews, labels

    # Load training data
    train_path = os.path.join(data_dir, 'train')
    X_train_pos, Y_train_pos = load_reviews(train_path, 'pos')
    X_train_neg, Y_train_neg = load_reviews(train_path, 'neg')

    X_train = X_train_pos + X_train_neg
    Y_train = Y_train_pos + Y_train_neg

    # Load test data
    test_path = os.path.join(data_dir, 'test')
    X_test_pos, Y_test_pos = load_reviews(test_path, 'pos')
    X_test_neg, Y_test_neg = load_reviews(test_path, 'neg')

    X_test = X_test_pos + X_test_neg
    Y_test = Y_test_pos + Y_test_neg

    # Shuffle the data
    import random
    random.seed(42)

    # Combine and shuffle training data
    train_data = list(zip(X_train, Y_train))
    random.shuffle(train_data)
    X_train, Y_train = zip(*train_data)

    # Combine and shuffle test data
    test_data = list(zip(X_test, Y_test))
    random.shuffle(test_data)
    X_test, Y_test = zip(*test_data)

    return list(X_train), list(Y_train), list(X_test), list(Y_test)

# Usage
X_train, Y_train, X_test, Y_test = load_imdb_from_directories('aclImdb')

print(f"Training reviews: {len(X_train)}")
print(f"Test reviews: {len(X_test)}")
print(f"Positive reviews in train: {sum(Y_train)}")
print(f"Negative reviews in train: {len(Y_train) - sum(Y_train)}")
```

---

### 🎯 Quick Start Template

```python
# Complete setup for Week 1 & 2
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# 1. Load data from Kaggle CSV
df = pd.read_csv('IMDB Dataset.csv')

# 2. Convert to required format
reviews = df['review'].values  # numpy array of strings
sentiments = (df['sentiment'] == 'positive').astype(int).values  # 1/0

# 3. Split 80/20
from sklearn.model_selection import train_test_split
X_train, X_test, Y_train, Y_test = train_test_split(
    reviews, sentiments,
    test_size=0.2,
    random_state=42,
    stratify=sentiments  # Maintain class balance
)

# 4. Optional: Use smaller subset for faster testing
# Use first 5000 for quick experiments
X_train_small = X_train[:4000]
Y_train_small = Y_train[:4000]
X_test_small = X_test[:1000]
Y_test_small = Y_test[:1000]

# 5. Verify data
print("="*50)
print("DATASET LOADED SUCCESSFULLY!")
print("="*50)
print(f"Training set: {len(X_train)} reviews")
print(f"  - Positive: {sum(Y_train)} ({sum(Y_train)/len(Y_train)*100:.1f}%)")
print(f"  - Negative: {len(Y_train)-sum(Y_train)} ({(len(Y_train)-sum(Y_train))/len(Y_train)*100:.1f}%)")
print(f"\nTest set: {len(X_test)} reviews")
print(f"  - Positive: {sum(Y_test)} ({sum(Y_test)/len(Y_test)*100:.1f}%)")
print(f"  - Negative: {len(Y_test)-sum(Y_test)} ({(len(Y_test)-sum(Y_test))/len(Y_test)*100:.1f}%)")
print("\nSample review:")
print(f"{X_train[0][:200]}...")
print(f"Label: {'Positive' if Y_train[0] == 1 else 'Negative'}")
```

---

### 📥 Option 2: Cornell Movie Review Dataset

**Alternative smaller dataset for quick testing**

- **URL**: http://www.cs.cornell.edu/people/pabo/movie-review-data/
- **Download**: http://www.cs.cornell.edu/people/pabo/movie-review-data/review_polarity.tar.gz
- **Size**: 2,000 reviews (1000 positive + 1000 negative)
- **Format**: Text files

**Loading code**:

```python
import os
import tarfile
import glob

# Extract
with tarfile.open('review_polarity.tar.gz', 'r:gz') as tar:
    tar.extractall()

# Load
pos_files = glob.glob('txt_sentoken/pos/*.txt')
neg_files = glob.glob('txt_sentoken/neg/*.txt')

X = []
Y = []

# Load positive reviews
for file in pos_files:
    with open(file, 'r', encoding='latin-1') as f:
        X.append(f.read())
        Y.append(1)

# Load negative reviews
for file in neg_files:
    with open(file, 'r', encoding='latin-1') as f:
        X.append(f.read())
        Y.append(0)

print(f"Loaded {len(X)} reviews")
```

---

## Week 3: Word Embeddings

### 📥 Pre-trained Word Embeddings

#### Option 1: Google News Word2Vec (Recommended)

**Best for**: Week 3 assignment

**Download Options**:

**A. Kaggle (Easiest)**

- **URL**: https://www.kaggle.com/datasets/adarshsng/googlenewsvectors
- **Size**: 1.5 GB
- **Format**: `.bin.gz` file

```bash
# Download via Kaggle CLI
kaggle datasets download -d adarshsng/googlenewsvectors

# Unzip
gunzip GoogleNews-vectors-negative300.bin.gz
```

**B. Google Drive (Original)**

- **URL**: https://drive.google.com/file/d/0B7XkCwpI5KDYNlNUTTlSS21pQmM/edit
- **Size**: 1.5 GB compressed
- **Note**: Manual download required

**C. Gensim API (Simplest)**

```python
import gensim.downloader as api

# Download and load (this will download ~1.5GB)
model = api.load('word2vec-google-news-300')

# Save to disk for future use
model.save('word2vec-google-news-300.model')
```

---

### 🔧 Loading and Converting Format

#### Required Format for Week 3:

```python
# Dictionary: word → 300D numpy array
word_embeddings = {
    'king': np.array([0.1, 0.2, ..., 0.3]),  # 300 dimensions
    'queen': np.array([0.15, 0.25, ..., 0.35]),
    'cat': np.array([...]),
    # ... etc
}
```

#### Loading from .bin file:

```python
from gensim.models import KeyedVectors
import numpy as np

# Load the binary file (this takes a few minutes)
print("Loading Word2Vec model... (this may take 2-3 minutes)")
model = KeyedVectors.load_word2vec_format(
    'GoogleNews-vectors-negative300.bin',
    binary=True
)

# Convert to dictionary format
word_embeddings = {}
for word in model.index_to_key:  # All words in vocabulary
    word_embeddings[word] = model[word]

print(f"Loaded {len(word_embeddings)} word vectors")
print(f"Each vector has {len(word_embeddings['king'])} dimensions")

# Test
print("\nTesting word similarity:")
print(f"king - man + woman = {model.most_similar(positive=['woman', 'king'], negative=['man'], topn=1)}")
```

#### Creating a Subset (Recommended):

Full dataset is huge (3M words × 300D). Create a subset:

```python
def create_word_embedding_subset(model, words_to_include=None, save_path='word_embeddings_subset.pkl'):
    """
    Create a subset of word embeddings

    Args:
        model: Loaded Word2Vec model
        words_to_include: List of words to include (None = use common words)
        save_path: Where to save the subset
    """
    import pickle

    if words_to_include is None:
        # Use most common words
        words_to_include = model.index_to_key[:50000]  # Top 50K words

    # Build subset dictionary
    subset = {}
    for word in words_to_include:
        if word in model:
            subset[word] = model[word]

    # Save
    with open(save_path, 'wb') as f:
        pickle.dump(subset, f)

    print(f"Saved {len(subset)} word vectors to {save_path}")
    return subset

# Usage
# Load full model once
model = KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

# Create subset with specific words
important_words = [
    'king', 'queen', 'man', 'woman', 'boy', 'girl',
    'happy', 'sad', 'joyful', 'angry', 'excited',
    'cat', 'dog', 'animal', 'pet',
    'oil', 'gas', 'petroleum', 'fuel', 'energy',
    'city', 'town', 'village', 'country', 'continent',
    # Add more words as needed
]

# Or just use top 10K most common words
subset = create_word_embedding_subset(model, important_words)

# Load subset later (much faster!)
import pickle
with open('word_embeddings_subset.pkl', 'rb') as f:
    word_embeddings = pickle.load(f)
```

---

#### Option 2: GloVe Embeddings (Alternative)

**Download from Stanford**:

- **URL**: https://nlp.stanford.edu/projects/glove/
- **Files**:
  - `glove.6B.zip` - 6B tokens, 400K vocab (Wikipedia 2014 + Gigaword 5)
  - Dimensions: 50D, 100D, 200D, 300D

**Loading GloVe**:

```python
import numpy as np

def load_glove_embeddings(file_path):
    """
    Load GloVe embeddings from text file

    Args:
        file_path: Path to glove.6B.300d.txt (or other dimension)

    Returns:
        Dictionary mapping words to vectors
    """
    embeddings = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            values = line.split()
            word = values[0]
            vector = np.array(values[1:], dtype='float32')
            embeddings[word] = vector

    return embeddings

# Usage
print("Loading GloVe embeddings...")
word_embeddings = load_glove_embeddings('glove.6B.300d.txt')
print(f"Loaded {len(word_embeddings)} words")
```

---

### 📊 Word Lists for Week 3

For **visualization exercises**, you'll need word lists:

```python
# Semantic clusters for PCA visualization
word_groups = {
    'emotions': ['happy', 'sad', 'joyful', 'angry', 'excited', 'pleased', 'delighted'],
    'energy': ['oil', 'gas', 'petroleum', 'fuel', 'energy', 'power'],
    'places': ['city', 'town', 'village', 'country', 'continent', 'nation', 'state'],
    'royalty': ['king', 'queen', 'prince', 'princess', 'monarch', 'royal'],
    'animals': ['cat', 'dog', 'bird', 'fish', 'lion', 'tiger', 'elephant']
}

# For analogies
analogy_tests = [
    ('king', 'queen', 'man'),  # Expect: woman
    ('king', 'queen', 'boy'),  # Expect: girl
    ('good', 'better', 'bad'),  # Expect: worse
    ('big', 'bigger', 'small'),  # Expect: smaller
]
```

---

## Week 4: Bilingual Embeddings & Tweets

### Part A: English-French Translation

#### 📥 English-French Word Pairs

**Option 1: MUSE Dataset (Recommended)**

- **URL**: https://github.com/facebookresearch/MUSE
- **Download**: https://dl.fbaipublicfiles.com/arrival/dictionaries/en-fr.txt

```python
import urllib.request

# Download dictionary
url = 'https://dl.fbaipublicfiles.com/arrival/dictionaries/en-fr.txt'
urllib.request.urlretrieve(url, 'en-fr.txt')

# Load
def load_bilingual_dict(file_path):
    """Load English-French word pairs"""
    en_fr = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            en_word, fr_word = line.strip().split()
            en_fr[en_word] = fr_word

    return en_fr

en_fr_dict = load_bilingual_dict('en-fr.txt')
print(f"Loaded {len(en_fr_dict)} translation pairs")

# Split into train/test
from sklearn.model_selection import train_test_split

items = list(en_fr_dict.items())
train_items, test_items = train_test_split(items, test_size=0.2, random_state=42)

en_fr_train = dict(train_items)
en_fr_test = dict(test_items)

print(f"Train: {len(en_fr_train)} pairs")
print(f"Test: {len(en_fr_test)} pairs")
```

**Option 2: Create Your Own**

```python
# Small custom dictionary for testing
en_fr_custom = {
    # Common words
    'hello': 'bonjour',
    'goodbye': 'au revoir',
    'thank you': 'merci',
    'yes': 'oui',
    'no': 'non',

    # Animals
    'cat': 'chat',
    'dog': 'chien',
    'bird': 'oiseau',

    # Numbers
    'one': 'un',
    'two': 'deux',
    'three': 'trois',

    # Colors
    'red': 'rouge',
    'blue': 'bleu',
    'green': 'vert',

    # More as needed...
}
```

#### 📥 French Word Embeddings

**Option 1: FastText French**

- **URL**: https://fasttext.cc/docs/en/crawl-vectors.html
- **Download**: https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.fr.300.bin.gz

```bash
# Download
wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.fr.300.bin.gz

# Unzip
gunzip cc.fr.300.bin.gz
```

**Load FastText**:

```python
from gensim.models import KeyedVectors

# Load French embeddings
fr_model = KeyedVectors.load_word2vec_format('cc.fr.300.bin', binary=True)

# Convert to dictionary
fr_embeddings = {}
for word in fr_model.index_to_key[:100000]:  # Top 100K
    fr_embeddings[word] = fr_model[word]

print(f"Loaded {len(fr_embeddings)} French word vectors")
```

**Option 2: Pre-processed Subset**

Create matched subset for your bilingual dictionary:

```python
def create_matched_embeddings(en_fr_dict, en_model, fr_model):
    """
    Create matched English and French embedding dictionaries

    Only includes words that exist in both dictionaries and both models
    """
    en_embeddings = {}
    fr_embeddings = {}

    valid_pairs = 0

    for en_word, fr_word in en_fr_dict.items():
        # Check if both words have embeddings
        if en_word in en_model and fr_word in fr_model:
            en_embeddings[en_word] = en_model[en_word]
            fr_embeddings[fr_word] = fr_model[fr_word]
            valid_pairs += 1

    print(f"Created matched embeddings for {valid_pairs} word pairs")

    return en_embeddings, fr_embeddings

# Usage
en_embeddings, fr_embeddings = create_matched_embeddings(
    en_fr_train,
    en_model,  # Google News Word2Vec
    fr_model   # French FastText
)
```

---

### Part B: Tweet Dataset for LSH

#### 📥 Twitter Sentiment Datasets

**Option 1: Sentiment140 (Best for LSH)**

- **URL**: https://www.kaggle.com/datasets/kazanova/sentiment140
- **Size**: 1.6 million tweets
- **Format**: CSV

```bash
kaggle datasets download -d kazanova/sentiment140
unzip sentiment140.zip
```

**Loading**:

```python
import pandas as pd

# Load tweets
df = pd.read_csv(
    'training.1600000.processed.noemoticon.csv',
    encoding='latin-1',
    header=None,
    names=['target', 'id', 'date', 'flag', 'user', 'text']
)

# Extract tweets
all_tweets = df['text'].tolist()

# Use subset for testing (Week 4 uses 10K tweets)
all_tweets_10k = all_tweets[:10000]

print(f"Loaded {len(all_tweets_10k)} tweets for LSH")
```

**Option 2: NLTK Twitter Corpus (Smaller)**

```python
import nltk
nltk.download('twitter_samples')

from nltk.corpus import twitter_samples

# Load tweets
positive_tweets = twitter_samples.strings('positive_tweets.json')
negative_tweets = twitter_samples.strings('negative_tweets.json')

all_tweets = list(positive_tweets) + list(negative_tweets)

print(f"Loaded {len(all_tweets)} tweets from NLTK")
```

---

### 🔧 Complete Week 4 Data Preparation

```python
# Complete script for Week 4

import numpy as np
import pickle
from gensim.models import KeyedVectors

# 1. Load English embeddings
print("Loading English embeddings...")
en_model = KeyedVectors.load_word2vec_format(
    'GoogleNews-vectors-negative300.bin',
    binary=True
)

# 2. Load French embeddings
print("Loading French embeddings...")
fr_model = KeyedVectors.load_word2vec_format(
    'cc.fr.300.bin',
    binary=True
)

# 3. Load bilingual dictionary
print("Loading bilingual dictionary...")
def load_dict(path):
    pairs = {}
    with open(path, 'r') as f:
        for line in f:
            en, fr = line.strip().split()
            pairs[en] = fr
    return pairs

en_fr_all = load_dict('en-fr.txt')

# 4. Split train/test
from sklearn.model_selection import train_test_split
items = list(en_fr_all.items())
train_items, test_items = train_test_split(items, test_size=0.2, random_state=42)

en_fr_train = dict(train_items[:5000])  # Use 5000 for training
en_fr_test = dict(test_items[:1500])    # Use 1500 for testing

# 5. Create matched embeddings
en_embeddings = {}
fr_embeddings = {}

for en_word, fr_word in en_fr_train.items():
    if en_word in en_model and fr_word in fr_model:
        en_embeddings[en_word] = en_model[en_word]
        fr_embeddings[fr_word] = fr_model[fr_word]

# 6. Load tweets
import pandas as pd
tweets_df = pd.read_csv(
    'training.1600000.processed.noemoticon.csv',
    encoding='latin-1',
    header=None,
    names=['target', 'id', 'date', 'flag', 'user', 'text']
)

all_tweets = tweets_df['text'].tolist()[:10000]

# 7. Save everything
print("\nSaving preprocessed data...")
with open('en_embeddings.pkl', 'wb') as f:
    pickle.dump(en_embeddings, f)

with open('fr_embeddings.pkl', 'wb') as f:
    pickle.dump(fr_embeddings, f)

with open('en_fr_train.pkl', 'wb') as f:
    pickle.dump(en_fr_train, f)

with open('en_fr_test.pkl', 'wb') as f:
    pickle.dump(en_fr_test, f)

with open('tweets.pkl', 'wb') as f:
    pickle.dump(all_tweets, f)

print("\n" + "="*50)
print("WEEK 4 DATA READY!")
print("="*50)
print(f"English embeddings: {len(en_embeddings)} words")
print(f"French embeddings: {len(fr_embeddings)} words")
print(f"Training pairs: {len(en_fr_train)}")
print(f"Test pairs: {len(en_fr_test)}")
print(f"Tweets: {len(all_tweets)}")
```

---

## Alternative Datasets

### For Quick Testing (All Weeks)

**Tiny Shakespeare (Text Classification)**

- 100KB of Shakespeare text
- Good for testing preprocessing pipelines

**20 Newsgroups (Classification)**

```python
from sklearn.datasets import fetch_20newsgroups

# Load
train = fetch_20newsgroups(subset='train')
test = fetch_20newsgroups(subset='test')

X_train = train.data
Y_train = train.target
```

### Custom Dataset Creation

```python
# Create synthetic sentiment data for testing
positive_templates = [
    "I love this {}!",
    "This {} is amazing!",
    "Great {} experience!",
    "Fantastic {}!",
    "Best {} ever!"
]

negative_templates = [
    "I hate this {}!",
    "This {} is terrible!",
    "Awful {} experience!",
    "Worst {}!",
    "Horrible {}!"
]

objects = ['movie', 'product', 'service', 'book', 'restaurant']

X_train = []
Y_train = []

for obj in objects:
    for template in positive_templates:
        X_train.append(template.format(obj))
        Y_train.append(1)

    for template in negative_templates:
        X_train.append(template.format(obj))
        Y_train.append(0)

print(f"Created {len(X_train)} synthetic reviews")
```

---

## Data Format Conversions

### Common Format Issues & Solutions

#### Issue 1: CSV Encoding Errors

```python
# Try different encodings
encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']

for encoding in encodings:
    try:
        df = pd.read_csv('data.csv', encoding=encoding)
        print(f"Success with {encoding}")
        break
    except:
        print(f"Failed with {encoding}")
```

#### Issue 2: Labels as Strings

```python
# Convert string labels to integers
df['sentiment_numeric'] = df['sentiment'].map({
    'positive': 1,
    'negative': 0,
    'pos': 1,
    'neg': 0,
    'Positive': 1,
    'Negative': 0
})
```

#### Issue 3: Missing Values

```python
# Remove NaN values
df = df.dropna(subset=['review', 'sentiment'])

# Or fill with empty string
df['review'] = df['review'].fillna('')
```

#### Issue 4: Imbalanced Classes

```python
from sklearn.utils import resample

# Separate majority and minority classes
df_majority = df[df.sentiment==1]
df_minority = df[df.sentiment==0]

# Downsample majority class
df_majority_downsampled = resample(df_majority,
                                  replace=False,
                                  n_samples=len(df_minority),
                                  random_state=42)

# Combine minority class with downsampled majority class
df_balanced = pd.concat([df_majority_downsampled, df_minority])

# Or upsample minority class
df_minority_upsampled = resample(df_minority,
                                replace=True,
                                n_samples=len(df_majority),
                                random_state=42)

df_balanced = pd.concat([df_majority, df_minority_upsampled])
```

---

## Troubleshooting

### Common Issues & Fixes

#### Memory Errors with Word2Vec

**Problem**: `MemoryError` when loading GoogleNews embeddings

**Solution 1**: Use 64-bit Python

```bash
python --version  # Check if 64-bit
```

**Solution 2**: Load subset only

```python
# Limit vocabulary
model = KeyedVectors.load_word2vec_format(
    'GoogleNews-vectors-negative300.bin',
    binary=True,
    limit=50000  # Only load top 50K words
)
```

**Solution 3**: Use gensim's API

```python
import gensim.downloader as api
model = api.load('word2vec-google-news-300')  # Handles memory better
```

---

#### Kaggle API Authentication

**Setup Kaggle API**:

1. Go to https://www.kaggle.com/account
2. Scroll to "API" section
3. Click "Create New API Token"
4. Download `kaggle.json`

**Linux/Mac**:

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

**Windows**:

```bash
mkdir %USERPROFILE%\.kaggle
move Downloads\kaggle.json %USERPROFILE%\.kaggle\
```

---

#### Download Speed Issues

**Use wget with progress bar**:

```bash
wget --progress=bar:force:noscroll [URL]
```

**Use aria2 for parallel downloading**:

```bash
aria2c -x 8 -s 8 [URL]  # 8 parallel connections
```

---

#### File Size Validation

```python
import os

def validate_file(path, expected_size_mb):
    """Check if file downloaded correctly"""
    if not os.path.exists(path):
        return False, "File not found"

    size_mb = os.path.getsize(path) / (1024 * 1024)

    if size_mb < expected_size_mb * 0.95:  # 5% tolerance
        return False, f"File incomplete: {size_mb:.1f}MB (expected {expected_size_mb}MB)"

    return True, f"File valid: {size_mb:.1f}MB"

# Usage
valid, msg = validate_file('GoogleNews-vectors-negative300.bin', 1500)
print(msg)
```

---

## Quick Reference: All Data Sources

### Week 1 & 2

- **Primary**: IMDB Kaggle Dataset (50K reviews)
  - URL: kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews
- **Alternative**: Stanford IMDB (50K reviews)
  - URL: ai.stanford.edu/~amaas/data/sentiment/
- **Backup**: Cornell Movie Reviews (2K reviews)
  - URL: cs.cornell.edu/people/pabo/movie-review-data/

### Week 3

- **Primary**: Google News Word2Vec (3M words, 300D)
  - Kaggle: kaggle.com/datasets/adarshsng/googlenewsvectors
  - Gensim: `api.load('word2vec-google-news-300')`
- **Alternative**: GloVe (400K words, multiple dimensions)
  - URL: nlp.stanford.edu/projects/glove/

### Week 4

- **English-French Dict**: MUSE (Facebook Research)
  - URL: github.com/facebookresearch/MUSE
- **French Embeddings**: FastText
  - URL: fasttext.cc/docs/en/crawl-vectors.html
- **Tweets**: Sentiment140 (1.6M tweets)
  - Kaggle: kaggle.com/datasets/kazanova/sentiment140
- **Alternative Tweets**: NLTK Twitter Corpus
  - `nltk.download('twitter_samples')`

---

## Complete Setup Script

```python
# Run this once to set up all datasets

import os
import urllib.request
import pickle
import pandas as pd
import numpy as np

def setup_all_datasets():
    """
    Complete setup for all 4 weeks
    Assumes you've manually downloaded large files
    """

    print("="*60)
    print("NLP COURSE DATA SETUP")
    print("="*60)

    # Week 1 & 2: Movie Reviews
    print("\n[1/4] Setting up movie reviews...")
    if os.path.exists('IMDB Dataset.csv'):
        df = pd.read_csv('IMDB Dataset.csv')
        print(f"✓ Found {len(df)} movie reviews")
    else:
        print("✗ Please download IMDB dataset from Kaggle")
        print("  URL: kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews")

    # Week 3: Word Embeddings
    print("\n[2/4] Setting up word embeddings...")
    if os.path.exists('GoogleNews-vectors-negative300.bin'):
        print("✓ Found Google News embeddings")
    else:
        print("✗ Please download Word2Vec from:")
        print("  Kaggle: kaggle.com/datasets/adarshsng/googlenewsvectors")
        print("  Or use: import gensim.downloader as api; api.load('word2vec-google-news-300')")

    # Week 4: Bilingual embeddings
    print("\n[3/4] Setting up bilingual data...")

    # Download EN-FR dictionary
    dict_url = 'https://dl.fbaipublicfiles.com/arrival/dictionaries/en-fr.txt'
    if not os.path.exists('en-fr.txt'):
        print("  Downloading EN-FR dictionary...")
        urllib.request.urlretrieve(dict_url, 'en-fr.txt')
        print("  ✓ Downloaded")
    else:
        print("  ✓ Found EN-FR dictionary")

    if os.path.exists('cc.fr.300.bin'):
        print("  ✓ Found French embeddings")
    else:
        print("  ✗ Please download French FastText from:")
        print("    URL: fasttext.cc/docs/en/crawl-vectors.html")

    # Week 4: Tweets
    print("\n[4/4] Setting up tweet dataset...")
    if os.path.exists('training.1600000.processed.noemoticon.csv'):
        print("✓ Found Sentiment140 tweets")
    else:
        print("✗ Please download Sentiment140 from:")
        print("  Kaggle: kaggle.com/datasets/kazanova/sentiment140")

    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Download any missing datasets (see URLs above)")
    print("2. Run preprocessing scripts for each week")
    print("3. Start coding the assignments!")

if __name__ == '__main__':
    setup_all_datasets()
```

---

## 🎉 You're Ready!

With these data sources and conversion scripts, you have everything needed to complete all 4 weeks of assignments!

**Pro Tips**:

1. Start with small subsets (1000 samples) to debug code quickly
2. Save preprocessed data to avoid reloading large files
3. Use pickle for Python objects, CSV for human-readable data
4. Always check data shapes before training
5. Keep a data preparation notebook for reference

**Happy coding!** 🚀
