import google.auth
from googleapiclient.discovery import build

def create_google_slides(summary_text):
    creds, _ = google.auth.default()
    service = build("slides", "v1", credentials=creds)
    
    presentation = service.presentations().create(body={"title": "RevAIse Summary"}).execute()
    slides_link = f"https://docs.google.com/presentation/d/{presentation['presentationId']}/edit"

    return slides_link