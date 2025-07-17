import os
import boto3
import uuid
import io
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from werkzeug.utils import secure_filename
from pydantic import BaseModel

# ====== Configuration ======
AWS_S3_BUCKET = 'rag-file-storage-bucket'  # <-- Change this!
ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx'}

s3 = boto3.client('s3')

app = FastAPI(title="S3 File Manager", 
              description="Upload, download, and manage files with AWS S3")

# Setup templates
templates = Jinja2Templates(directory="templates")

# ====== Models ======
class FileInfo(BaseModel):
    id: str
    key: str
    size: float
    last_modified: str

class FileListResponse(BaseModel):
    success: bool
    files: list[FileInfo] = []
    error: Optional[str] = None

class Metadata(BaseModel):
    id: str
    filename: str
    author: str
    language: str
    date_added: datetime
    size: int # in bytes
    file_type: str
    source_filename: str
    pages: int
    status: int
    s3_key: str

# ====== Helper functions ======
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_file_size(file: UploadFile) -> int:
    """Calculate file size using seek and tell method"""
    file.file.seek(0, 2)  # Seek to end of file
    file_size = file.file.tell()  # Get current position (file size)
    file.file.seek(0)  # Reset to beginning for upload
    return file_size

# ====== Routes ======

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, message: Optional[str] = None, message_type: Optional[str] = None):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "message": message,
        "message_type": message_type
    })

@app.get("/list-files", response_model=FileListResponse)
async def list_files():
    """List all files in the S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=AWS_S3_BUCKET)
        files = []

        if 'Contents' in response:
            for item in response['Contents']:
                # Extract ID from S3 key (format: "uuid/filename")
                s3_key = item['Key']
                file_id = s3_key.split('/')[0] if '/' in s3_key else 'unknown'
                
                files.append(FileInfo(
                    id=file_id,
                    key=s3_key,
                    size=round(item['Size'] / 1024, 2),
                    last_modified=item['LastModified'].isoformat()
                ))
        
        return FileListResponse(success=True, files=files)
    except Exception as e:
        return FileListResponse(success=False, error=str(e))

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(""),
    authors: str = Form(""),
    language: str = Form("")
):
    """Upload a file to S3 with metadata"""
    
    # Validate file
    if not file.filename:
        return RedirectResponse(url="/?message=No selected file&message_type=error", status_code=303)
    
    if not allowed_file(file.filename):
        return RedirectResponse(url="/?message=Invalid file type (allowed: pdf, xls, xlsx)&message_type=error", status_code=303)
    
    try:
        # Get file size
        file_size = calculate_file_size(file)
        
        # Prepare file information
        source_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_s3_key = f"{file_id}/{source_filename}"
        file_type = source_filename.rsplit('.', 1)[-1].lower() if '.' in source_filename else ''
        
        # Store metadata
        metadata = Metadata(
            id=file_id,
            filename=filename.strip(),
            author=authors.strip(),
            language=language,
            date_added=datetime.now(),
            size=file_size,
            file_type=file_type,
            source_filename=source_filename,
            pages=0,
            status=0,  # 0: uploaded not processed, 1: processed
            s3_key=file_s3_key
        )
        
        # Save metadata to RDS
        print(metadata.model_dump())

        # Upload to S3
        s3.upload_fileobj(
            file.file, 
            AWS_S3_BUCKET, 
            file_s3_key, 
            ExtraArgs={
                'Metadata': {
                    'id': file_id,
                },
                'ContentType': file.content_type or 'application/octet-stream'
            }
        )
        
        return RedirectResponse(url=f"/?message=File {file_s3_key} uploaded successfully&message_type=success", status_code=303)
    
    except Exception as e:
        return RedirectResponse(url=f"/?message=ERROR UPLOADING FILE: {str(e)}&message_type=error", status_code=303)


# Note: s3_key is formated as uuid/filename
# BUT fastapi can't directly take s3_key as parameter as it will segment by /
# Solution: use s3_key:path to tell fastapi to treat uuid/filename as a single parameter
@app.get("/download/{s3_key:path}")
async def download_file(s3_key: str):
    """Download a file from S3"""
    try:
        # Get file from S3
        response = s3.get_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        file_content = response['Body'].read()
        
        # Get original filename from s3_key
        source_filename = s3_key.split('/')[-1]
        
        # Create streaming response
        def generate():
            yield file_content
        
        return StreamingResponse(
            generate(),
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={source_filename}"}
        )
    except Exception as e:
        return RedirectResponse(url=f"/?message=ERROR DOWNLOADING FILE: {str(e)}&message_type=error", status_code=303)

@app.get("/delete/{s3_key:path}")
async def delete_file(s3_key: str):
    """Delete a file from S3"""
    try:
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        return RedirectResponse(url=f"/?message=File {s3_key} deleted successfully&message_type=success", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?message=ERROR DELETING FILE: {str(e)}&message_type=error", status_code=303)

# ====== Health Check ======
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=8000, reload=True) 