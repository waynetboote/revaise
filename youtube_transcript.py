from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(youtube_url):
    video_id = youtube_url.split("v=")[1].split("&")[0]
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([entry["text"] for entry in transcript])