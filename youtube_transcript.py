from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import re

def extract_video_id(youtube_url):
    """Extracts the YouTube Video ID from different URL formats."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, youtube_url)
    if match:
        return match.group(1)
    return None  # Return None if no valid video ID is found

def get_transcript(youtube_url):
    """Uses Selenium to extract YouTube subtitles (bypasses API restrictions)."""
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return "Error: Invalid YouTube URL. Please enter a correct YouTube link."

    try:
        # Configure Selenium (headless browser)
        options = Options()
        options.add_argument("--headless")  # Run in background (no GUI)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Open YouTube video
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        driver.get(video_url)
        time.sleep(5)  # Allow page to load

        # Try to enable captions (if not already enabled)
        try:
            cc_button = driver.find_element("xpath", "//button[@aria-label='Turn on captions']")
            cc_button.click()
            time.sleep(3)
        except:
            pass  # Captions might already be on

        # Extract transcript text
        transcript_text = ""
        captions = driver.find_elements("xpath", "//div[contains(@class,'captions-text')]")
        for caption in captions:
            transcript_text += caption.text + " "

        driver.quit()  # Close browser

        if not transcript_text:
            return "Error: Could not retrieve transcript from YouTube."

        return transcript_text.strip()

    except Exception as e:
        return f"Error: Unexpected error - {str(e)}"
