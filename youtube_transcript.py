from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re

def extract_video_id(youtube_url):
    """Extracts the YouTube Video ID from different URL formats"""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, youtube_url)
    if match:
        return match.group(1)
    return None  # Return None if no valid video ID is found

def get_transcript(youtube_url):
    video_id = extract_video_id(youtube_url)
    
    if not video_id:
        return "Error: Invalid YouTube URL. Please enter a correct YouTube link."

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except TranscriptsDisabled:
        return "Error: This video does not have subtitles available."
    except NoTranscriptFound:
        return "Error: No transcript found for this video."
    except Exception as e:
        return f"Error: An unexpected error occurred - {str(e)}"
