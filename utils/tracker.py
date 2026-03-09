import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta

def log_view(db, user_id):
    # Render Tracker tab
    # Form for new session
    # Dataframe to show history and calculation
    st.subheader("Study Tracker")
    
    with st.form("tracker_form"):
        topic = st.text_input("Study Topic")
        duration = st.number_input("Duration (minutes)", min_value=1, step=1)
        notes = st.text_area("Optional Notes")
        if st.form_submit_button("Log Session"):
            # Calculate session number
            sessions = list(db.tracker.find({"user_id": user_id}).sort("date"))
            session_number = len(sessions) + 1
            
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            ist_now = datetime.now(ist_tz)
            
            # Insert session
            db.tracker.insert_one({
                "user_id": user_id,
                "session_number": session_number,
                "date": ist_now,
                "topic": topic,
                "duration_min": duration,
                "notes": notes
            })
            st.success("Session logged!")
            st.rerun()

    st.subheader("Your Study History")
    # Fetch all logs for user
    logs = list(db.tracker.find({"user_id": user_id}).sort("date", -1))
    if logs:
        # Convert to pandas dataframe
        for log in logs:
            log["_id"] = str(log["_id"])
            log["date"] = log["date"].strftime("%Y-%m-%d %H:%M:%S")
            if "session_number" not in log:
                log["session_number"] = "-"
        df = pd.DataFrame(logs)[["session_number", "date", "topic", "duration_min", "notes"]]
        st.dataframe(df, use_container_width=True)
        
        # Calculate total duration
        total_mins = df["duration_min"].sum()
        st.metric("Total Study Hours", f"{total_mins / 60:.2f} hrs")
    else:
        st.info("No study sessions logged yet.")

def highlight_btn(db, user_id, content: str, chunk_id: str):
    # Minimal highlight save logic
    # Usually called from inside chat interface
    # Simple form or button
    if st.button("⭐ Highlight this response", key=f"hl_{chunk_id}"):
        db.highlights.insert_one({
            "user_id": user_id,
            "chunk_id": chunk_id,
            "note": content,
            "date": datetime.utcnow()
        })
        st.toast("Highlight saved to database!")
