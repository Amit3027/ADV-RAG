import streamlit as st
import numpy as np
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer
import utils.tracker as tracker

@st.cache_resource
def load_embedder():
    # Cache embedder mock to avoid 2GB download during simulation
    class MockEmbedder:
        def encode(self, text):
            # Return dummy 1024 dim embedding
            return np.zeros(1024, dtype='float32')
    return MockEmbedder()

def build_index(db, user_id, doc_id=None):
    # Fetch specific chunk for user based on doc_id (or all if None)
    # Build FAISS index of 1024 dims
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
    
    # Initialize FAISS IndexFlatIP
    dimension = 1024
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_np)
    
    return index, all_chunks

def get_groq_client():
    # Initialize Groq client
    # Fetches from secrets
    api_key = st.secrets["groq"]["api_key"]
    if api_key == "dummy_key":
        return None
    return Groq(api_key=api_key)

def query(db, user_id):
    # Main RAG querying interface
    # Chat UI, search index, Groq generation
    # Shows highlight buttons
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
        
    for i, msg in enumerate(st.session_state[messages_key]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                chunk_id = f"chat_{selected_doc_id}_{i}"
                tracker.highlight_btn(db, user_id, msg["content"], chunk_id)
            
    prompt = st.chat_input("Ask a question about this document...")
    if prompt:
        from bson.objectid import ObjectId
        # Display user input
        st.session_state[messages_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if selected_doc_id == "all":
                    index, all_chunks = build_index(db, user_id, None)
                else:
                    index, all_chunks = build_index(db, user_id, ObjectId(selected_doc_id))
                    
                if not index:
                    response = "No indexed content found in this selection!"
                    st.markdown(response)
                    st.session_state[messages_key].append({"role": "assistant", "content": response})
                    return
                    
                # Search FAISS (top 5 chunks)
                embedder = load_embedder()
                query_emb = embedder.encode(prompt).astype('float32').reshape(1, -1)
                distances, indices = index.search(query_emb, 5)
                
                # Format context
                contexts = []
                for idx in indices[0]:
                    if idx < len(all_chunks):
                        chunk = all_chunks[idx]
                        c_text = f"[{chunk['title']} #{chunk['number']} ({chunk['start']}-{chunk['end']}s)]: {chunk['text']}"
                        contexts.append(c_text)
                
                context_str = "\n".join(contexts)
                
                # Load prompt file
                try:
                    with open("prompt.txt", "r") as f:
                        system_prompt = f.read()
                except FileNotFoundError:
                    system_prompt = "Context:\n{context}\n\nStudent Query: {query}"
                    
                sys_msg = system_prompt.replace("{context}", context_str).replace("{query}", prompt)
                
                try:
                    client = get_groq_client()
                    if client is None:
                        response = f"Simulated response: HighlightRAG Tutor would answer your query: {prompt}"
                    else:
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": sys_msg},
                                {"role": "user", "content": prompt}
                            ],
                            model="llama-3.1-8b-instant",
                            temperature=0.1
                        )
                        response = chat_completion.choices[0].message.content
                except Exception as e:
                    response = f"Error generating response: {e}"
                    
                st.markdown(response)
                
        st.session_state[messages_key].append({"role": "assistant", "content": response})
        st.rerun()
