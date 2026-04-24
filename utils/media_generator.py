from google import genai
import streamlit as st
import datetime

def get_gemini_client():
    """Initialize and return a Gemini client using the new google-genai SDK."""
    if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
        api_key = st.secrets["gemini"]["api_key"]
        if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE" and api_key != "dummy_key":
            return genai.Client(api_key=api_key)
    return None

def generate_diagram_mermaid(query, context):
    """Generate a Mermaid.js diagram using Gemini API."""
    client = get_gemini_client()
    if not client:
        return "graph TD;\nA[Dummy Server]-->B[Mermaid Diagram];\nB-->C[To view this you need a valid Gemini API key];"
        
    prompt = f"""You are an expert Diagram generator. Generate a Mermaid.js diagram code that explains the following topic: '{query}'.
    Use the following course context if relevant:
    {context}
    
    IMPORTANT: Provide ONLY valid Mermaid diagram code. Do not include markdown code block syntax (like ```mermaid or ```), just the raw code.
    If it's impossible to create a Mermaid diagram, create a simple flowchart: flowchart TD; A[Error] --> B[Cannot create diagram].
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        text = response.text.strip()
        # Clean up if the model still returns markdown block
        if text.startswith('```mermaid'):
            text = text[10:]
            if text.endswith('```'):
                text = text[:-3]
        elif text.startswith('```'):
            text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
        return text.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "graph TD;\n    A[Rate Limit] --> B[Please wait a minute and try again];\n    B --> C[Free tier has limited requests per minute];"
        return f"graph TD;\n    Error[Error: {error_msg[:80]}]"

def generate_video_script(query, context):
    """Generate an educational video script using Gemini API."""
    client = get_gemini_client()
    if not client:
        return "### Simulated Video Script\n\n**Visual:** Visual representation of concept\n**Audio:** Audio description.\n\n*Configure the Gemini API key in secrets.toml to generate real scripts.*"
        
    prompt = f"""You are an expert educational video producer. Create a short, highly engaging storyboard and video script for a 1-2 minute video explaining the concept: '{query}'.
    Use the following course context if relevant:
    {context}
    
    Format the output nicely using Markdown cards or tables. Include 'Visual', 'Audio' (Script), and 'On-Screen Text' for each scene.
    Keep it concise, modern, and effective for study.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "⏳ **Rate limit reached.** Please wait about a minute and try again. Free tier has limited requests per minute."
        return f"Error generating script: {error_msg}"

def save_generated_media(db, user_id, query, media_type, content, doc_id=""):
    """Save generated media metadata to MongoDB."""
    try:
        media_doc = {
            "user_id": str(user_id),
            "query": query,
            "media_type": media_type,
            "content": content,
            "doc_id": str(doc_id) if doc_id else "",
            "timestamp": datetime.datetime.utcnow()
        }
        db.generated_media.insert_one(media_doc)
        return True
    except Exception as e:
        return False
