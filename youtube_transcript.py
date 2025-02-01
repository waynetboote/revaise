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
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prioritize manually added English subtitles
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            transcript = None  # English (manual) not found

        # If no manual English, use auto-generated English
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except:
                return "Error: No English transcript available."

        # Fetch the transcript and return the text
        return " ".join([entry["text"] for entry in transcript.fetch()])
    
    except TranscriptsDisabled:
        return "Error: This video does not allow transcript access."
    except NoTranscriptFound:
        return "Error: No transcript found for this video."
    except Exception as e:
        return f"Error: Unexpected error - {str(e)}"
