from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def get_transcript(youtube_url):
    video_id = youtube_url.split("v=")[1].split("&")[0]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except TranscriptsDisabled:
        return "Error: This video does not have subtitles available."
    except NoTranscriptFound:
        return "Error: No transcript found for this video."
    except Exception as e:
        return f"Error: An unexpected error occurred - {str(e)}"
