# youtube_transcript.py
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# --- Monkey-patch requests.get to include a custom User-Agent ---
_old_get = requests.get

def custom_get(*args, **kwargs):
    # Ensure we have a headers dictionary
    headers = kwargs.get('headers', {})
    # Set a default User-Agent if one isn’t already provided
    if 'User-Agent' not in headers:
        headers['User-Agent'] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.93 Safari/537.36"
        )
    kwargs['headers'] = headers
    return _old_get(*args, **kwargs)

# Apply the monkey-patch
requests.get = custom_get
# ------------------------------------------------------------

def extract_video_id(youtube_url):
    """
    Extract the 11-character video ID from a valid YouTube URL.
    Returns the video ID if found and if the URL is from an allowed YouTube domain;
    otherwise, returns None.
    """
    from urllib.parse import urlparse
    parsed_url = urlparse(youtube_url)
    allowed_domains = {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}
    
    if parsed_url.netloc not in allowed_domains:
        return None

    match = re.search(r"(?:v=|youtu\.be/|embed/|v/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript(youtube_url):
    """
    Retrieve the transcript text from a YouTube URL.
    Returns the transcript as a string or an error message.
    """
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Error: Invalid YouTube URL."
    
    try:
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(entry["text"] for entry in transcript_entries)
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"
