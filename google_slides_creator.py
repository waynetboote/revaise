# google_slides_creator.py
import google.auth
from googleapiclient.discovery import build

def create_google_slides(summary_text):
    """
    Create a Google Slides presentation with the summary text added to a textbox on a new slide.
    Returns the edit link for the newly created presentation.
    """
    creds, _ = google.auth.default()
    service = build("slides", "v1", credentials=creds)
    
    # Create a new presentation.
    presentation = service.presentations().create(body={"title": "RevAIse Summary"}).execute()
    presentation_id = presentation.get("presentationId")
    
    # Create a new slide using the 'BLANK' layout.
    create_slide_request = {
        "createSlide": {
            "objectId": "MySlide_01",
            "insertionIndex": "1",
            "slideLayoutReference": {
                "predefinedLayout": "BLANK"
            }
        }
    }
    
    # Create a textbox shape on the new slide.
    create_shape_request = {
        "createShape": {
            "objectId": "MyTextBox_01",
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": "MySlide_01",
                "size": {
                    "height": {"magnitude": 200, "unit": "PT"},
                    "width": {"magnitude": 400, "unit": "PT"}
                },
                "transform": {
                    "scaleX": 1,
                    "scaleY": 1,
                    "translateX": 50,
                    "translateY": 50,
                    "unit": "PT"
                }
            }
        }
    }
    
    # Insert the summary text into the textbox.
    insert_text_request = {
        "insertText": {
            "objectId": "MyTextBox_01",
            "insertionIndex": 0,
            "text": summary_text
        }
    }
    
    requests = [create_slide_request, create_shape_request, insert_text_request]
    
    service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests}
    ).execute()
    
    slides_link = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
    return slides_link
