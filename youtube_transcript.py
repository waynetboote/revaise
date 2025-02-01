# youtube_transcript.py
import re
from youtube_transcript_api import YouTubeTranscriptApi

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
        # Set a custom User-Agent header. This makes the request appear as if it is coming from a typical browser.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.93 Safari/537.36"
            )
        }
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id, headers=headers)
        transcript_text = " ".join(entry["text"] for entry in transcript_entries)
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"
