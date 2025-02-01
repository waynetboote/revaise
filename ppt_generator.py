# ppt_generator.py
from pptx import Presentation
from pptx.util import Inches

def create_pptx(summary_text, filename="revaise_presentation.pptx"):
    """
    Create a PowerPoint presentation containing the summary text.
    Returns the filename of the saved presentation.
    """
    prs = Presentation()
    
    # Use a slide layout that includes a title placeholder (adjust the index as needed).
    slide_layout = prs.slide_layouts[0]  # typically the title slide
    slide = prs.slides.add_slide(slide_layout)
    
    # Set the slide title.
    if slide.shapes.title:
        slide.shapes.title.text = "RevAIse Summary"
    
    # Add a textbox for the summary.
    left = Inches(1)
    top = Inches(2)
    width = Inches(8)
    height = Inches(2)
    textbox = slide.shapes.add_textbox(left, top, width, height)
    text_frame = textbox.text_frame
    text_frame.text = summary_text
    
    prs.save(filename)
    return filename
