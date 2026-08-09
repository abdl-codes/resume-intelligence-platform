"""
Standard-Library Text Processing Utilities
Provides tokenization, sentence splitting, stopword filtering, n-gram extraction,
and rule-based stemming without external packages.
"""
import re
from typing import List, Tuple, Set

# Comprehensive built-in English stopwords set
ENGLISH_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}


def tokenize(text: str, keep_case: bool = False) -> List[str]:
    """
    Extracts word tokens from raw text using standard regular expressions.
    Preserves programming tokens like C++, C#, .NET, Node.js when possible.
    """
    if not keep_case:
        text = text.lower()
    
    # Custom token pattern to capture technology words like C++, C#, .net
    pattern = r'[a-zA-Z0-9_\+\#\.\-]+'
    tokens = re.findall(pattern, text)
    
    # Filter out pure punctuation tokens like single dots/hyphens
    cleaned_tokens = []
    for token in tokens:
        stripped = token.strip(".-")
        if stripped:
            cleaned_tokens.append(token if token in ("c++", "c#", ".net") else stripped)
    
    return cleaned_tokens


def split_sentences(text: str) -> List[str]:
    """
    Splits text into clean sentences using regex rules to handle common sentence boundaries.
    """
    if not text or not text.strip():
        return []
    
    # Normalize newlines
    normalized = re.sub(r'\r\n|\r', '\n', text)
    
    # Replace newline bullet points with period sentence boundaries
    normalized = re.sub(r'\n\s*[\-\*\•\d+\.]\s*', '. ', normalized)
    
    # Split on terminal punctuation followed by space or newline
    sentence_candidates = re.split(r'(?<=[.!?])\s+', normalized)
    
    sentences = []
    for candidate in sentence_candidates:
        cleaned = candidate.strip()
        # Filter out empty or single-character noise
        if len(cleaned) > 2:
            sentences.append(cleaned)
            
    return sentences


def remove_stopwords(tokens: List[str], custom_stopwords: Set[str] = None) -> List[str]:
    """
    Removes common English stopwords from token list.
    """
    stopwords = ENGLISH_STOPWORDS if custom_stopwords is None else custom_stopwords
    return [t for t in tokens if t.lower() not in stopwords]


def get_ngrams(tokens: List[str], n: int = 2) -> List[Tuple[str, ...]]:
    """
    Generates contiguous n-grams from a list of tokens.
    """
    if len(tokens) < n or n < 1:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def simple_stem(word: str) -> str:
    """
    Standard-library rule-based suffix stemming helper.
    """
    word = word.lower()
    if len(word) <= 3:
        return word
    
    # Strip common plurals first
    if word.endswith("s") and not word.endswith("ss") and len(word) > 4:
        word = word[:-1]
    
    suffixes = [
        ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
        ("izer", "ize"), ("bli", "ble"), ("alli", "al"), ("entli", "ent"),
        ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
        ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
        ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"),
        ("ing", ""), ("ed", ""), ("es", "")
    ]
    
    for suffix, replacement in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)] + replacement
            
    return word
