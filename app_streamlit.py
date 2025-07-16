import streamlit as st
import boto3
import io
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd

# ====== Configuration ======
AWS_S3_BUCKET = 'rag-file-storage-bucket'  # Same as Flask app
ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx'}

# Initialize S3 client
@st.cache_resource
def init_s3_client():
    return boto3.client('s3')

s3 = init_s3_client()

# ====== Helper functions ======
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def list_s3_files():
    """Fetch files from S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=AWS_S3_BUCKET)
        files = []

        if 'Contents' in response:
            for item in response['Contents']:
                files.append({
                    'Filename': item['Key'],
                    'Size (KB)': round(item['Size'] / 1024, 2),
                    'Last Modified': item['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Key': item['Key']  # For internal use
                })
        
        return files
    except Exception as e:
        st.error(f"Error listing files: {str(e)}")
        return []

def upload_to_s3(file, filename):
    """Upload file to S3"""
    try:
        s3.upload_fileobj(
            file, 
            AWS_S3_BUCKET, 
            filename,
            ExtraArgs={
                'Metadata': {
                    'id': str(uuid.uuid4()),
                },
                'ContentType': file.type if hasattr(file, 'type') else 'application/octet-stream'
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)

def download_from_s3(filename):
    """Download file from S3"""
    try:
        file_obj = io.BytesIO()
        s3.download_fileobj(AWS_S3_BUCKET, filename, file_obj)
        file_obj.seek(0)
        return file_obj, None
    except Exception as e:
        return None, str(e)

def delete_from_s3(filename):
    """Delete file from S3"""
    try:
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=filename)
        return True, None
    except Exception as e:
        return False, str(e)

# ====== Streamlit App ======
def main():
    st.set_page_config(
        page_title="S3 File Manager",
        page_icon="📁",
        layout="wide"
    )
    
    st.title("📁 S3 File Manager")
    st.markdown("---")
    
    # File Upload Section
    st.subheader("Upload File")
    
    uploaded_file = st.file_uploader(
        "Choose a file", 
        type=['pdf', 'xls', 'xlsx'],
        help="Allowed file types: PDF, XLS, XLSX"
    )
    
    if uploaded_file is not None:
        if st.button("Upload", type="primary"):
            if allowed_file(uploaded_file.name):
                filename = secure_filename(uploaded_file.name)
                
                with st.spinner(f"Uploading {filename}..."):
                    success, error = upload_to_s3(uploaded_file, filename)
                    
                if success:
                    st.success(f"File {filename} uploaded successfully!")
                    st.rerun()  # Refresh to show new file in list
                else:
                    st.error(f"Error uploading file: {error}")
            else:
                st.error("Invalid file type. Allowed: PDF, XLS, XLSX")
    
    st.markdown("---")
    
    # File List Section
    st.subheader("Files in S3 Bucket")
    
    # Refresh button
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Get file list
    files = list_s3_files()
    
    if not files:
        st.info("No files found in the bucket.")
    else:
        # Create DataFrame for display
        df = pd.DataFrame(files)
        display_df = df[['Filename', 'Size (KB)', 'Last Modified']].copy()
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("### File Actions")
        
        # Action buttons for each file
        for i, file_info in enumerate(files):
            filename = file_info['Key']
            col1, col2, col3, col4 = st.columns([3, 1, 1, 3])
            
            with col1:
                st.text(filename)
            
            with col2:
                # Download button
                if st.button("⬇️ Download", key=f"download_{i}"):
                    with st.spinner(f"Downloading {filename}..."):
                        file_obj, error = download_from_s3(filename)
                        
                    if file_obj:
                        st.download_button(
                            label=f"Click to save {filename}",
                            data=file_obj,
                            file_name=filename,
                            mime='application/octet-stream',
                            key=f"save_{i}"
                        )
                    else:
                        st.error(f"Error downloading file: {error}")
            
            with col3:
                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{i}", type="secondary"):
                    # Confirmation dialog using session state
                    st.session_state[f"confirm_delete_{i}"] = True
            
            # Handle delete confirmation
            if st.session_state.get(f"confirm_delete_{i}", False):
                st.warning(f"Are you sure you want to delete {filename}?")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("Yes, Delete", key=f"confirm_yes_{i}", type="primary"):
                        with st.spinner(f"Deleting {filename}..."):
                            success, error = delete_from_s3(filename)
                        
                        if success:
                            st.success(f"File {filename} deleted successfully!")
                            st.session_state[f"confirm_delete_{i}"] = False
                            st.rerun()
                        else:
                            st.error(f"Error deleting file: {error}")
                
                with col_no:
                    if st.button("Cancel", key=f"confirm_no_{i}"):
                        st.session_state[f"confirm_delete_{i}"] = False
                        st.rerun()
            
            st.markdown("---")

if __name__ == "__main__":
    main() 