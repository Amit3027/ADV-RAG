import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import re
import os
import tempfile

@st.cache_resource
def load_embedder():
    # Cache the real sentence-transformer model for embeddings
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def load_whisper():
    # Mock whisper
    class MockWhisper:
        def transcribe(self, file_path, task, language):
            class Seg:
                def __init__(self, t):
                    self.text = t
                    self.start = 0.0
                    self.end = 1.0
            return [Seg("Mock transcription text for simulation.")], None
    return MockWhisper()

def process_mp4(file_path: str, filename: str):
    # Transcribe MP4 using whisper
    # Extract title/number using regex
    # Return list of chunks with embeddings
    model = load_whisper()
    # Translate to English if needed, but requirements say "hi" / translate
    segments, _ = model.transcribe(file_path, task="translate", language="hi")
    
    # Parse title and number like process_incoming.py
    title = filename
    number = "N/A"
    match = re.search(r'#(\d+)', filename)
    if match:
        number = match.group(1)
        
    chunks = []
    embedder = load_embedder()
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        # Adapt user's chunks: chunk['embedding'] = model.encode(chunk['text'])
        embedding = embedder.encode(text).tolist()
        chunks.append({
            "title": title,
            "number": number,
            "start": segment.start,
            "end": segment.end,
            "text": text,
            "embedding": embedding
        })
    return chunks

def process_pdf(file_path: str, filename: str):
    # Extract text from PDF
    # Chunk into 500 characters
    # Return list of chunks with embeddings
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        if page.extract_text():
            full_text += page.extract_text() + " "
        
    title = filename
    number = "N/A"
    
    chunks = []
    embedder = load_embedder()
    chunk_size = 500
    for i in range(0, len(full_text), chunk_size):
        text = full_text[i:i+chunk_size].strip()
        if not text:
            continue
        # Encode chunks
        embedding = embedder.encode(text).tolist()
        chunks.append({
            "title": title,
            "number": number,
            "start": round((i / len(full_text)) * 100, 2) if len(full_text) > 0 else 0,
            "end": round(((i + chunk_size) / len(full_text)) * 100, 2) if len(full_text) > 0 else 0,
            "text": text,
            "embedding": embedding
        })
    return chunks

def upload_process(db, user_id):
    # Render upload tab interface
    st.subheader("Upload Course Material")
    
    # 1. Show existing files
    st.markdown("### Your Documents")
    existing_docs = list(db.transcripts.find({"user_id": user_id}))
    if existing_docs:
        for doc in existing_docs:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 **{doc['filename']}**")
            with col2:
                if st.button("Delete", key=f"del_{doc['_id']}"):
                    db.transcripts.delete_one({"_id": doc["_id"]})
                    st.toast(f"Deleted {doc['filename']}")
                    st.rerun()
    else:
        st.info("No documents uploaded yet.")
        
    st.markdown("---")
    st.markdown("### Upload New")
        
    uploaded_file = st.file_uploader("Upload an MP4 or PDF", type=["mp4", "pdf"])
    
    if st.button("Process Document") and uploaded_file:
        with st.spinner("Processing... This may take a while."):
            filename = uploaded_file.name
            
            # Check if file already exists
            if db.transcripts.find_one({"user_id": user_id, "filename": filename}):
                st.warning(f"File '{filename}' already exists. Please delete it first if you want to re-upload.")
                return
                
            # Save file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.type.split('/')[-1] if '/' in uploaded_file.type else 'tmp'}") as tmp:
                tmp.write(uploaded_file.getbuffer())
                temp_path = tmp.name
                
            try:
                if filename.endswith(".mp4"):
                    chunks = process_mp4(temp_path, filename)
                else:
                    chunks = process_pdf(temp_path, filename)
                    
                if chunks:
                    # Insert to transcripts collection
                    db.transcripts.insert_one({
                        "user_id": user_id, 
                        "filename": filename,
                        "chunks": chunks
                    })
                    st.success(f"Successfully processed and indexed {filename}!")
                    st.rerun()
                else:
                    st.warning("No extractable content found in the file.")
            except Exception as e:
                st.error(f"Error processing file: {e}")
            finally:
                os.remove(temp_path)
