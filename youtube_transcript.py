from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_transcript(youtube_url):
    """Uses Selenium to extract YouTube subtitles (bypasses API restrictions)."""
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return "Error: Invalid YouTube URL. Please enter a correct YouTube link."

    try:
        chrome_binary_path, chromedriver_path = download_chromium()  # Ensure Chromium and ChromeDriver are installed

        # Configure Selenium with Chromium
        options = Options()
        options.binary_location = chrome_binary_path
        options.add_argument("--headless")  # Run in background (no GUI)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)

        # Open YouTube video
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        driver.get(video_url)

        # Wait for captions to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.ytp-caption-segment"))
            )
        except:
            return "Error: Captions not found or failed to load."

        # Extract transcript text
        transcript_text = ""
        captions = driver.find_elements(By.CSS_SELECTOR, "span.ytp-caption-segment")
        for caption in captions:
            transcript_text += caption.text + " "

        driver.quit()  # Close browser

        if not transcript_text:
            return "Error: Could not retrieve transcript from YouTube."

        return transcript_text.strip()

    except Exception as e:
        return f"Error: Unexpected error - {str(e)}"
