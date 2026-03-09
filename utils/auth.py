import streamlit as st
import bcrypt
import smtplib
from email.mime.text import MIMEText
import secrets
import hashlib
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    # Generate bcrypt hash
    # Encode string to utf-8
    # Return decoded string
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    # Check provided password against hash
    # Needs utf-8 encoding for both
    # Return boolean result
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def send_email(to_email: str, link: str):
    """Send password reset email. If SMTP credentials are not configured, display the link in the UI."""
    # Check if email secrets are provided
    email_cfg = st.secrets.get("email", {})
    sender = email_cfg.get("sender")
    password = email_cfg.get("password")
    if not sender or not password or sender == "dummy@example.com":
        # No SMTP configured – alert the user instead of displaying the link
        st.error("Email not configured in `.streamlit/secrets.toml`. Password reset unavailable.")
        return
    try:
        msg = MIMEText(f"Reset your password here: {link}")
        msg["Subject"] = "Password Reset for HighlightRAG Tutor"
        msg["From"] = sender
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
    except Exception as e:
        st.error(f"Failed to send email: {e}")

def change_pass(db, user_id):
    # Render change password form in profile tab
    # Check old password
    # Update hash if matched
    st.subheader("Change Password")
    with st.form("change_pass_form"):
        old_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        if st.form_submit_button("Update Password"):
            user = db.users.find_one({"_id": user_id})
            if user and check_password(old_pass, user["password_hash"]):
                db.users.update_one({"_id": user_id}, {"$set": {"password_hash": hash_password(new_pass)}})
                st.success("Password updated successfully!")
            else:
                st.error("Incorrect current password.")

def login_form(db):
    # Render login form
    # Handle auth logic
    # Set session state variables {logged_in, user_id, username}
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = db.users.find_one({"email": email})
            # Check user and password
            if user and check_password(password, user["password_hash"]):
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user["_id"]
                st.session_state["username"] = user["username"]
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid email or password.")

def signup_form(db):
    # Render signup form
    # Check unique email
    # Hash password and insert
    st.subheader("Sign Up")
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if db.users.find_one({"email": email}):
                st.error("Email is already registered.")
            elif username and email and len(password) >= 6:
                # Insert new user with hashed password
                db.users.insert_one({
                    "username": username,
                    "email": email,
                    "password_hash": hash_password(password)
                })
                st.success("Registration successful! Please login.")
            else:
                st.error("Please fill all fields. Password > 5 chars.")

def forgot_form(db):
    # Render forgot password form
    # Generate urlsafe token
    # Insert hash into reset_tokens collection
    st.subheader("Forgot Password")
    with st.form("forgot_pass"):
        email = st.text_input("Enter your registered email")
        if st.form_submit_button("Send Reset Link"):
            user = db.users.find_one({"email": email})
            if user:
                # Generate secure token
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                # Store in reset_tokens with 15 mins expiry
                db.reset_tokens.insert_one({
                    "user_id": user["_id"],
                    "token_hash": token_hash,
                    "expiry": datetime.utcnow() + timedelta(minutes=15)
                })
                # Base URL configuration (fallback to localhost)
                base_url = "http://localhost:8503" 
                link = f"{base_url}/?token={token}"
                send_email(email, link)
            # Always show success for security to avoid email enumeration
            st.success("If the email is registered and email secrets are configured, a reset link has been sent.")

def check_reset_token(db) -> bool:
    # Check if reset token exists in URL
    # Prompt for new password
    # Update hash and delete token
    # Return True if handled
    query_params = st.query_params
    if "token" in query_params:
        token = query_params["token"]
        st.subheader("Reset Password")
        with st.form("reset_pass"):
            new_password = st.text_input("New Password", type="password")
            if st.form_submit_button("Update Password"):
                hashed_token = hashlib.sha256(token.encode()).hexdigest()
                reset_doc = db.reset_tokens.find_one({"token_hash": hashed_token})
                # Verify validity and expiry
                if reset_doc and reset_doc["expiry"] > datetime.utcnow():
                    db.users.update_one(
                        {"_id": reset_doc["user_id"]},
                        {"$set": {"password_hash": hash_password(new_password)}}
                    )
                    db.reset_tokens.delete_one({"_id": reset_doc["_id"]})
                    st.success("Password reset! You can now login. Please clear URL token.")
                else:
                    st.error("Invalid or expired token.")
        return True
    return False

def render_auth(db):
    # Main entry point for unauthenticated users
    # Check for password reset flow first
    # Otherwise render Login/Signup/Forgot tabs
    if check_reset_token(db):
        return

    tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Forgot Password"])
    with tab1: login_form(db)
    with tab2: signup_form(db)
    with tab3: forgot_form(db)
