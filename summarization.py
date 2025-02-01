import nltk
from nltk.tokenize import sent_tokenize

nltk.download("punkt")

def summarize_text(text, num_sentences=5):
    sentences = sent_tokenize(text)
    return " ".join(sentences[:num_sentences])