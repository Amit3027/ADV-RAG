import streamlit as st
import numpy as np
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer
import utils.tracker as tracker
import utils.media_generator as media_gen

@st.cache_resource
def load_embedder():
    # Cache the real sentence-transformer model for embeddings
    return SentenceTransformer('all-MiniLM-L6-v2')

def build_index(db, user_id, doc_id=None):
    # Fetch specific chunk for user based on doc_id (or all if None)
    # Build FAISS index
    # Return index and chunks list
    if doc_id:
        document = db.transcripts.find_one({"_id": doc_id, "user_id": user_id})
        docs = [document] if document else []
    else:
        docs = list(db.transcripts.find({"user_id": user_id}))
        
    if not docs:
        return None, []
        
    all_chunks = []
    for doc in docs:
        all_chunks.extend(doc.get("chunks", []))
        
    if not all_chunks:
        return None, []
        
    # Extract embeddings
    embeddings = [c["embedding"] for c in all_chunks]
    embeddings_np = np.array(embeddings).astype('float32')
    
    # Detect dimension from actual data
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings_np)
    index.add(embeddings_np)
    
    return index, all_chunks

def get_groq_client():
    # Initialize Groq client
    api_key = st.secrets["groq"]["api_key"]
    if api_key == "dummy_key":
        return None
    return Groq(api_key=api_key)

def detect_media_intent(prompt):
    """Detect if user wants a diagram, video script, or regular answer."""
    prompt_lower = prompt.lower()
    
    diagram_keywords = [
        "draw", "diagram", "flowchart", "visualize", "chart",
        "mermaid", "graph", "sketch", "illustrate", "map out",
        "flow chart", "mind map", "architecture", "design diagram"
    ]
    video_keywords = [
        "video", "video script", "storyboard", "animate", 
        "create a video", "make a video", "video explanation"
    ]
    
    if any(kw in prompt_lower for kw in video_keywords):
        return "video"
    if any(kw in prompt_lower for kw in diagram_keywords):
        return "diagram"
    return "text"

def get_context_from_index(db, user_id, selected_doc_id, prompt):
    """Build FAISS index, search, and return context string + chunks."""
    from bson.objectid import ObjectId
    
    if selected_doc_id == "all":
        index, all_chunks = build_index(db, user_id, None)
    else:
        index, all_chunks = build_index(db, user_id, ObjectId(selected_doc_id))
    
    if not index:
        return None, None, []
    
    # Search FAISS (top 5 chunks)
    embedder = load_embedder()
    query_emb = embedder.encode(prompt).astype('float32').reshape(1, -1)
    faiss.normalize_L2(query_emb)
    distances, indices = index.search(query_emb, 5)
    
    # Format context
    contexts = []
    for idx in indices[0]:
        if idx < len(all_chunks):
            chunk = all_chunks[idx]
            c_text = f"[{chunk['title']} #{chunk['number']} ({chunk['start']}-{chunk['end']})]: {chunk['text']}"
            contexts.append(c_text)
    
    context_str = "\n".join(contexts)
    return index, context_str, all_chunks

def query(db, user_id):
    # Main RAG querying interface
    st.subheader("Chat with Course Material")
    
    # Let user select document
    existing_docs = list(db.transcripts.find({"user_id": user_id}))
    if not existing_docs:
        st.info("Please upload some course material first!")
        return
        
    doc_options = {"all": "All Documents 📚"}
    doc_options.update({str(doc['_id']): f"📄 {doc['filename']}" for doc in existing_docs})
    
    selected_doc_id = st.selectbox("Select document to interact with", 
                                  options=list(doc_options.keys()), 
                                  format_func=lambda x: doc_options[x],
                                  key="chat_doc_select")
    
    st.markdown("---")
    
    # Ensure messages specific to document
    if f"messages_{selected_doc_id}" not in st.session_state:
        st.session_state[f"messages_{selected_doc_id}"] = []
        
    messages_key = f"messages_{selected_doc_id}"
        
    # Render previous messages
    for i, msg in enumerate(st.session_state[messages_key]):
        with st.chat_message(msg["role"]):
            if msg.get("type") == "diagram":
                st.markdown(msg["content"])
                st.markdown("**📊 Mermaid Diagram:**")
                st.code(msg["mermaid_code"], language="mermaid")
            elif msg.get("type") == "video":
                st.markdown(msg["content"])
            else:
                st.markdown(msg["content"])
            if msg["role"] == "assistant":
                chunk_id = f"chat_{selected_doc_id}_{i}"
                tracker.highlight_btn(db, user_id, msg["content"], chunk_id)
            
    prompt = st.chat_input("Ask a question, or say 'draw ...' for diagrams, 'video ...' for scripts...")
    if prompt:
        # Display user input
        st.session_state[messages_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Get context from FAISS
                index, context_str, all_chunks = get_context_from_index(
                    db, user_id, selected_doc_id, prompt
                )
                
                if index is None:
                    response = "No indexed content found in this selection!"
                    st.markdown(response)
                    st.session_state[messages_key].append({"role": "assistant", "content": response})
                    st.rerun()
                    return
                
                # Detect what the user wants
                intent = detect_media_intent(prompt)
                
                if intent == "diagram":
                    # ---- DIAGRAM via Gemini (media_generator.py) ----
                    mermaid_code = media_gen.generate_diagram_mermaid(prompt, context_str)
                    
                    response = f"📊 **Diagram generated for:** *{prompt}*"
                    st.markdown(response)
                    st.markdown("**Mermaid Diagram Code:**")
                    st.code(mermaid_code, language="mermaid")
                    
                    # Save to MongoDB
                    media_gen.save_generated_media(
                        db, user_id, prompt, "diagram", mermaid_code, selected_doc_id
                    )
                    
                    st.session_state[messages_key].append({
                        "role": "assistant",
                        "content": response,
                        "type": "diagram",
                        "mermaid_code": mermaid_code
                    })
                    
                elif intent == "video":
                    # ---- VIDEO SCRIPT via Gemini (media_generator.py) ----
                    script = media_gen.generate_video_script(prompt, context_str)
                    
                    response = f"🎬 **Video Script generated for:** *{prompt}*\n\n{script}"
                    st.markdown(response)
                    
                    # Save to MongoDB
                    media_gen.save_generated_media(
                        db, user_id, prompt, "video_script", script, selected_doc_id
                    )
                    
                    st.session_state[messages_key].append({
                        "role": "assistant",
                        "content": response,
                        "type": "video"
                    })
                    
                else:
                    # ---- STANDARD RAG Q&A via Groq ----
                    try:
                        with open("prompt.txt", "r") as f:
                            system_prompt = f.read()
                    except FileNotFoundError:
                        system_prompt = "Context:\n{context}\n\nStudent Query: {query}"
                        
                    sys_msg = system_prompt.replace("{context}", context_str).replace("{query}", prompt)
                    
                    try:
                        client = get_groq_client()
                        if client is None:
                            response = f"Simulated response for: {prompt}"
                        else:
                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": sys_msg},
                                    {"role": "user", "content": prompt}
                                ],
                                model="llama-3.1-8b-instant",
                                temperature=0.3
                            )
                            response = chat_completion.choices[0].message.content
                    except Exception as e:
                        response = f"Error generating response: {e}"
                        
                    st.markdown(response)
                    st.session_state[messages_key].append({"role": "assistant", "content": response})
        
        st.rerun()
