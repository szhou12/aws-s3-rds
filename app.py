import streamlit as st
import os
import time
from datetime import datetime, timezone
import boto3


# Configuration
S3_BUCKET = "your-s3-bucket-name"
S3_PREFIX = "uploads/"   # Optional, for organizing files in S3

# Initialize S3 client (uses AWS credentials from env or config file)
s3_client = boto3.client("s3")


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory metadata store (replace with DB later)
metadata_store = []

st.title("Staff Document Upload Demo")

# Upload form
with st.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Choose a file to upload")
    title = st.text_input("Document Title")
    author = st.text_input("Author")
    language = st.selectbox("Language", 
                           options=["English", "中文"],
                           index=0)  # Default to English
    submit = st.form_submit_button("Upload")

    if submit and uploaded_file and title and author:
        # 1. Save file locally -> S3
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{uploaded_file.name}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 2. Save metadata (add to in-memory store) -> RDS
        metadata = {
            "filename": filename,
            "title": title,
            "author": author,
            "language": language,
            "upload_time": timestamp,
            "file_path": file_path,
            "status": "uploaded"
        }
        metadata_store.append(metadata)

        st.success("File uploaded successfully!")

        # 3. Simulate background processing (asynchronous in real world)
        st.info("Simulating background processing...")
        # For demo, do it in-place with time.sleep (replace with real async job later)
        time.sleep(2)  # Simulate processing delay
        print(f"[{filename}] Processing: extracting text...")
        time.sleep(2)  # Simulate embedding delay
        print(f"[{filename}] Processing: generating embeddings...")
        time.sleep(1)
        print(f"[{filename}] Done processing.")
        metadata["status"] = "processed"
        st.success("File processed!")

# Show uploaded docs (current session)
if metadata_store:
    st.header("Uploaded Documents")
    for meta in metadata_store:
        st.write(meta)
