import streamlit as st
from pymongo import MongoClient
import utils.auth as auth
import utils.transcription as transcription
import utils.rag as rag
import utils.tracker as tracker
import utils.notes as notes
import os

# Configure the Streamlit page
st.set_page_config(
    page_title="HighlightRAG Tutor",
    page_icon="🎓",
    layout="wide"
)

@st.cache_resource
def init_db():
    # Initialize connection to MongoDB using credentials in secrets
    # Return database object
    if "mongo" in st.secrets:
        uri = st.secrets["mongo"]["uri"]
        if uri == "dummy_uri":
            import mongomock
            client = mongomock.MongoClient()
        else:
            client = MongoClient(uri)
        return client.rag_tutor_db
    return None

db = init_db()

def main():
    # Main driver function
    st.title("🎓 HighlightRAG Tutor Online")
    
    # Initialize session state for login status
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not db:
        st.error("Database not configured. Please check `.streamlit/secrets.toml` (copy from secrets.toml.example).")
        st.stop()

    # Route request based on auth guard
    if not st.session_state["logged_in"]:
        auth.render_auth(db)
    else:
        # User is logged in, show app interface
        st.sidebar.write(f"Welcome back, **{st.session_state['username']}**!")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        # Render main tabs
        tab_up, tab_chat, tab_notes, tab_track, tab_prof = st.tabs([
            "Upload Materials 📤", 
            "Course Chat 💬", 
            "My Notes 📓", 
            "Study Tracker ⏱️", 
            "Profile ⚙️"
        ])

        with tab_up:
            # Delegate to transcription utility
            transcription.upload_process(db, str(st.session_state["user_id"]))
            
        with tab_chat:
            # Delegate to RAG querying
            rag.query(db, str(st.session_state["user_id"]))
            
        with tab_notes:
            # Delegate to notes management
            notes.manage(db, str(st.session_state["user_id"]))
            
        with tab_track:
            # Delegate to session tracker
            tracker.log_view(db, str(st.session_state["user_id"]))
            
        with tab_prof:
            # Delegate to auth profile settings
            auth.change_pass(db, st.session_state["user_id"])

if __name__ == "__main__":
    main()
