# HighlightRAG Tutor Online

A modular Streamlit application for NIT CS students providing RAG capabilities, notes, study tracking, and robust authentication.

## Local Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Secrets:**
   Copy `secrets.toml.example` to `.streamlit/secrets.toml` and fill in your actual credentials:
   - MongoDB connection URI
   - Groq API Key
   - Gmail SMTP app password

3. **Run Application:**
   ```bash
   streamlit run app.py
   ```

## Deployment on Railway

1. Push this repository to GitHub.
2. Link the repository to your Railway project.
3. Configure Environment Variables in Railway to match secrets.toml structure:
   - Make sure Streamlit secrets format works with env vars or set them via Railway's file injection to `.streamlit/secrets.toml`.
   - Start Command will automatically be inferred as `streamlit run app.py`.

## Simulated Testing Workflow
- Create a user via Sign Up tab.
- Upload an MP4 or PDF on the Upload tab.
- Ask a related question on the Chat tab (e.g. "What is HTML?") and see cited context.
- Ask an unrelated question (e.g. "What is the Weather?") and see the boundaries applied.
- Highlight an important answer.
- Go to Notes tab to create categorized colored notes.
- Use Tracker to save your study session progress.
