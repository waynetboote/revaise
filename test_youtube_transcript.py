# test_youtube_transcript.py
from youtube_transcript import extract_video_id, get_transcript

# Replace with a valid YouTube URL that you know has a transcript
valid_url = "https://www.youtube.com/watch?v=x3c1ih2NJEg"
invalid_url = "https://www.notyoutube.com/watch?v=12345678901"

def test_extract_video_id():
    video_id = extract_video_id(valid_url)
    assert video_id is not None, "Video ID should be extracted"
    print("Extracted Video ID:", video_id)

def test_invalid_url():
    video_id = extract_video_id(invalid_url)
    assert video_id is None, "Invalid URL should not extract a video ID"
    print("Correctly handled invalid URL.")

def test_get_transcript():
    transcript = get_transcript(valid_url)
    if transcript.startswith("Error"):
        print("Error fetching transcript:", transcript)
    else:
        print("Transcript fetched successfully.")
    
if __name__ == "__main__":
    test_extract_video_id()
    test_invalid_url()
    test_get_transcript()
