# youtube_transcript.py
import re
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(youtube_url):
    """
    Extract the 11-character video ID from a valid YouTube URL.
    Returns the video ID if the URL is from an allowed YouTube domain;
    otherwise, returns None.
    """
    parsed_url = urlparse(youtube_url)
    allowed_domains = {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}
    
    # Normalize the domain for a case-insensitive comparison
    if parsed_url.netloc.lower() not in allowed_domains:
        return None

    match = re.search(r"(?:v=|youtu\.be/|embed/|v/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript(youtube_url):
    """
    Retrieve the transcript text from a YouTube URL.
    Returns a dict with keys:
      - 'success': True if successful, False otherwise
      - 'transcript': The transcript text (if successful)
      - 'error': An error message (if unsuccessful)
    """
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return {"success": False, "error": "Invalid YouTube URL."}
    
    try:
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        transcript_text = " ".join(entry["text"] for entry in transcript_entries)
        return {"success": True, "transcript": transcript_text}
    except Exception as e:
        return {"success": False, "error": f"Error fetching transcript: {str(e)}"}
