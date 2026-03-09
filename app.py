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
    page_title="RAG Tutor Online",
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
    st.markdown("""
        <style>
        /* Hide Default Elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Typography */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }

        /* Glassmorphic App Background */
        .stApp {
            background: radial-gradient(circle at top right, rgba(0,255,170,0.1), transparent 40%),
                        radial-gradient(circle at bottom left, rgba(0,136,255,0.1), transparent 40%),
                        #0F172A;
            color: #F8FAFC;
        }

        /* Glass Sidebar */
        div[data-testid="stSidebar"] {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 4px 0 24px rgba(0,0,0,0.4);
        }

        /* Styling Inputs & Cards */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
            background-color: rgba(15, 23, 42, 0.5) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #F8FAFC !important;
            border-radius: 8px !important;
        }
        
        .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
            border-color: #00FFAA !important;
            box-shadow: 0 0 10px rgba(0,255,170,0.3) !important;
        }

        /* Advanced Buttons */
        .stButton>button {
            border-radius: 12px;
            background: linear-gradient(90deg, #00FFAA 0%, #0088FF 100%);
            border: none;
            color: #0F172A !important;
            font-weight: 600;
            padding: 0.5rem 1rem;
            box-shadow: 0 4px 15px rgba(0, 136, 255, 0.3);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        .stButton>button:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 8px 25px rgba(0, 255, 170, 0.5);
            color: #0F172A !important;
            border: none;
        }

        /* Tab Pill Design */
        button[data-baseweb="tab"] {
            border-radius: 20px 20px 0 0;
            transition: all 0.3s ease;
        }
        button[data-baseweb="tab"]:hover {
            background-color: rgba(30, 41, 59, 0.5);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🎓 RAG Tutor Online")
    
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
        try:
            st.sidebar.image("logo.svg", use_container_width=True)
        except Exception:
            pass
            
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
