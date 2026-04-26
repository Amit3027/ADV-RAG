from google import genai
import streamlit as st
import datetime
import time
import base64
import urllib.parse

def get_gemini_client():
    """Initialize and return a Gemini client using the new google-genai SDK."""
    if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
        api_key = st.secrets["gemini"]["api_key"]
        if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE" and api_key != "dummy_key":
            return genai.Client(api_key=api_key)
    return None

def _call_gemini_with_retry(client, prompt, max_retries=3):
    """Call Gemini API with automatic retry on rate limit errors."""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            if ("429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                time.sleep(wait_time)
                continue
            raise e
    return None

def _trim_context(context, max_chars=2000):
    """Trim context to avoid exceeding API limits."""
    if context and len(context) > max_chars:
        return context[:max_chars] + "\n...[trimmed for brevity]"
    return context

def render_mermaid_image(mermaid_code):
    """Render a Mermaid diagram as an image in Streamlit using mermaid.ink."""
    try:
        # Encode the mermaid code to base64 for the mermaid.ink API
        graph_bytes = mermaid_code.encode("utf-8")
        base64_str = base64.urlsafe_b64encode(graph_bytes).decode("ascii")
        img_url = f"https://mermaid.ink/img/{base64_str}?theme=dark&bgColor=0F172A"
        st.image(img_url, caption="AI Generated Diagram", use_container_width=True)
        return True
    except Exception:
        return False

def generate_diagram_mermaid(query, context):
    """Generate a Mermaid.js diagram using Gemini API."""
    client = get_gemini_client()
    if not client:
        return "graph TD;\nA[No API Key]-->B[Configure Gemini API key in secrets.toml];"
    
    context = _trim_context(context)
    
    prompt = f"""You are an expert Diagram generator. Generate a Mermaid.js diagram code that explains the following topic: '{query}'.
    Use the following course context if relevant:
    {context}
    
    IMPORTANT RULES:
    1. Provide ONLY valid Mermaid diagram code.
    2. Do NOT include markdown code block syntax (like ```mermaid or ```).
    3. Use simple node labels without special characters like parentheses or quotes inside brackets.
    4. Prefer 'graph TD' or 'flowchart TD' syntax.
    5. Keep it clean and readable with 5-10 nodes maximum.
    """
    try:
        text = _call_gemini_with_retry(client, prompt)
        if not text:
            return "graph TD;\n    A[Error] --> B[No response from AI];"
        text = text.strip()
        # Clean up if the model still returns markdown block
        if text.startswith('```mermaid'):
            text = text[len('```mermaid'):].strip()
        if text.startswith('```'):
            text = text[3:].strip()
        if text.endswith('```'):
            text = text[:-3].strip()
        return text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "graph TD;\n    A[Rate Limit] --> B[Please wait 1-2 minutes and try again];\n    B --> C[Free tier: 15 requests per minute];"
        return f"graph TD;\n    A[Error: {error_msg[:60]}]"

def generate_video_script(query, context):
    """Generate an educational video script using Gemini API."""
    client = get_gemini_client()
    if not client:
        return "### ⚠️ No API Key\n\nConfigure the Gemini API key in secrets.toml to generate video scripts."
    
    context = _trim_context(context)
    
    prompt = f"""You are an expert educational video producer. Create a short, highly engaging storyboard and video script for a 1-2 minute video explaining the concept: '{query}'.
    Use the following course context if relevant:
    {context}
    
    Format the output nicely using Markdown. For each scene include:
    - 🎬 **Scene [number]**: [title]
    - 📸 **Visual**: What appears on screen
    - 🎙️ **Narration**: What the narrator says
    - 📝 **On-Screen Text**: Key text overlays
    
    Keep it concise (4-6 scenes), modern, and effective for study.
    """
    try:
        text = _call_gemini_with_retry(client, prompt)
        if not text:
            return "### ⚠️ Error\n\nNo response received from AI. Please try again."
        return text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "### ⏳ Rate Limit Reached\n\nPlease wait 1-2 minutes and try again. The free tier allows about 15 requests per minute."
        return f"### ⚠️ Error\n\n{error_msg}"

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
