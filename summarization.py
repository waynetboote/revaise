# summarization.py
import nltk
from nltk.tokenize import sent_tokenize
from nltk.data import find

# Ensure that the 'punkt' tokenizer is available.
try:
    find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def summarize_text(text, num_sentences=5):
    """
    Summarize the input text by returning the first `num_sentences` sentences.
    If the text is empty or no sentences are found, an appropriate message is returned.
    """
    if not isinstance(text, str) or not text.strip():
        return "No text provided for summarization."
    
    sentences = sent_tokenize(text)
    if not sentences:
        return "No valid sentences found for summarization."
    
    return " ".join(sentences[:num_sentences])
