# youtube_transcript.py
import re
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi

import re
from urllib.parse import urlparse

def extract_video_id(youtube_url):
    """
    Extract the 11-character video ID from a valid YouTube URL.
    Returns the video ID if the URL is from an allowed YouTube domain;
    otherwise, returns None.
    """
    # Parse the URL to get its components
    parsed_url = urlparse(youtube_url)
    
    # Define the set of allowed YouTube domains
    allowed_domains = {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}
    
    # Check if the URL's domain (netloc) is in our allowed set
    if parsed_url.netloc not in allowed_domains:
        return None

    # Use a regex to extract the 11-character video ID
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
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        transcript_text = " ".join(entry["text"] for entry in transcript_entries)
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"
