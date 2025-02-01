from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(youtube_url):
    video_id = youtube_url.split("v=")[1].split("&")[0]
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

def get_transcript(youtube_url):
    video_id = youtube_url.split("v=")[1].split("&")[0]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except TranscriptsDisabled:
        return "Error: This video does not have subtitles available."

    return " ".join([entry["text"] for entry in transcript])
