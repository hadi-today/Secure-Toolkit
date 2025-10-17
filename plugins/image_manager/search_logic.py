import re
from . import config

# Basic English stop words. For a real app, use a library like NLTK.
STOP_WORDS = set([
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were',
    'will', 'with'
])

def extract_keywords(text):
    # 1. Extract hashtags
    hashtags = re.findall(r'#(\w+)', text)
    
    # 2. Clean text
    text = re.sub(r'#\w+', '', text) # Remove hashtags
    text = re.sub(r'https?://\S+', '', text) # Remove URLs
    text = re.sub(r'[^\w\s]', '', text).lower() # Remove punctuation, lowercase
    
    # 3. Tokenize and remove stop words
    words = [word for word in text.split() if word not in STOP_WORDS]
    
    # 4. Combine and unique
    keywords = set(hashtags + words)
    return list(keywords)

def rank_results(results, keywords):
    ranked = []
    for item in results:
        score = 0
        tags = item['tags'].lower() if item['tags'] else ''
        desc = item['description'].lower() if item['description'] else ''
        
        for keyword in keywords:
            if f',{keyword},' in f',{tags},': # Exact tag match
                score += config.TAG_MATCH_SCORE
            elif keyword in desc:
                score += config.DESC_MATCH_SCORE
        
        if score > 0:
            ranked.append({'item': item, 'score': score})
            
    return sorted(ranked, key=lambda x: x['score'], reverse=True)