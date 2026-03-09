import streamlit as st
from datetime import datetime

# Helper dict for color codes
COLORS = {
    "yellow": "#FFFF00",
    "green": "#00FF00",
    "blue": "#0000FF",
    "red": "#FF0000",
    "orange": "#FFA500"
}

def manage(db, user_id):
    # Render Notes tab
    # Form for adding new colored notes
    # List view for reading old notes
    st.subheader("Your Notes")
    
    with st.form("new_note_form"):
        content = st.text_area("Write or paste notes here")
        color_name = st.selectbox("Highlight Color", list(COLORS.keys()))
        if st.form_submit_button("Save Note"):
            # Insert to database
            db.notes.insert_one({
                "user_id": user_id,
                "content": content,
                "color": COLORS[color_name],
                "timestamp": datetime.utcnow()
            })
            st.success("Note saved!")
            st.rerun()
            
    st.divider()
    st.subheader("Saved Notes")
    
    # Inject CSS for Book/PDF page look
    st.markdown("""
        <style>
        .book-page-container {
            background-color: #fcfbf9;
            color: #2b2b2b;
            padding: 40px 60px;
            margin-bottom: 40px;
            border-radius: 4px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1), 0 1px 8px rgba(0,0,0,0.06);
            font-family: 'Georgia', serif;
            line-height: 1.8;
            font-size: 18px;
            border: 1px solid #eae5d9;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        .book-page-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #eae5d9;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        .color-dot {
            height: 14px;
            width: 14px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
            border: 1px solid #ccc;
        }
        </style>
    """, unsafe_allow_html=True)

    # Query all user notes, sort by timestamp ascending (1) to keep the first writing on top
    notes = list(db.notes.find({"user_id": user_id}).sort("timestamp", 1))
    if not notes:
        st.info("No notes found.")
        return
        
    for idx, note in enumerate(notes, 1):
        color_hex = note["color"]
        date_str = note["timestamp"].strftime('%B %d, %Y • %I:%M %p')
        # Simple text formatting
        content = note["content"].replace("\n", "<br>")
        
        html_content = f"""
        <div class="book-page-container">
            <div class="book-page-header">
                <div><strong>Page {idx}</strong></div>
                <div>
                    <span class="color-dot" style="background-color: {color_hex};"></span>
                    {date_str}
                </div>
            </div>
            <div style="text-align: justify;">
                {content}
            </div>
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)
