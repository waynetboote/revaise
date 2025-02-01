from youtube_transcript_api import YouTubeTranscriptApi
import re

def extract_video_id(youtube_url):
    match = re.search(r"(?<=v=|youtu\.be/|embed/|v/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript(youtube_url):
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Error: Invalid YouTube URL."
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"
