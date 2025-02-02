# summarization.py
import nltk
from nltk.tokenize import sent_tokenize
from nltk.data import find
import logging

logger = logging.getLogger(__name__)

def ensure_punkt():
    """
    Ensure that the NLTK 'punkt' tokenizer is available.
    If not, attempt to download it while handling possible race conditions.
    """
    try:
        find('tokenizers/punkt')
    except LookupError:
        try:
            # Attempt to download the 'punkt' package quietly.
            nltk.download('punkt', quiet=True)
            logger.info("'punkt' package downloaded successfully.")
        except Exception as e:
            # Catch exceptions such as FileExistsError that might occur during concurrent unzipping.
            logger.warning("Exception occurred during 'punkt' download: %s", e)
            # Optionally, you could try checking again after a brief pause.
            try:
                find('tokenizers/punkt')
            except LookupError:
                raise RuntimeError("Failed to download or locate the 'punkt' tokenizer.") from e

# Ensure that the 'punkt' tokenizer is available.
ensure_punkt()

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
