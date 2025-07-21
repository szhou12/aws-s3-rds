import os
from dotenv import load_dotenv
import boto3
import uuid
import io
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from werkzeug.utils import secure_filename
from pydantic import BaseModel, MySQLDsn
from sqlmodel import Session, select

from db import get_db, db_manager
from models import FileInfo, FileListResponse, Upload


load_dotenv()

db_host = os.getenv("MYSQL_HOST")
db_port = os.getenv("MYSQL_PORT")
db_user = os.getenv("MYSQL_USER")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DB_NAME")


# ====== Configuration ======
AWS_S3_BUCKET = 'rag-file-storage-bucket'  # <-- Change this!
ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx'}

s3 = boto3.client('s3')



# Add lifespan event management: load once before the app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_uri = MySQLDsn.build(
        scheme="mysql+pymysql", # MySQL driver
        username=db_user,
        password=db_password,
        host=db_host,
        port=3306,
        path=db_name  # Important: Include '/' before DB name
    )
    
    db_manager.init_db(str(db_uri))
    yield
    # Shutdown cleanup if needed

app = FastAPI(lifespan=lifespan, 
              title="S3 File Manager", 
              description="Upload, download, and manage files with AWS S3")

# Setup templates
templates = Jinja2Templates(directory="templates")


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

# @app.get("/list-files", response_model=FileListResponse)
# async def list_files():
#     """List all files in the S3 bucket"""
#     try:
#         response = s3.list_objects_v2(Bucket=AWS_S3_BUCKET)
#         files = []

#         if 'Contents' in response:
#             for item in response['Contents']:
#                 # Extract ID from S3 key (format: "uuid/filename")
#                 s3_key = item['Key']
#                 file_id = s3_key.split('/')[0] if '/' in s3_key else 'unknown'
                
#                 files.append(FileInfo(
#                     id=file_id,
#                     key=s3_key,
#                     size=round(item['Size'] / 1024, 2),
#                     last_modified=item['LastModified'].isoformat()
#                 ))
        
#         return FileListResponse(success=True, files=files)
#     except Exception as e:
#         return FileListResponse(success=False, error=str(e))

@app.get("/list-files", response_model=FileListResponse)
async def list_files(session: Session = Depends(get_db)):
    """List all files from database metadata"""
    try:
        statement = select(Upload)
        uploads = session.exec(statement).all()
        files = []
        for upload in uploads:
            files.append(FileInfo(
                id=upload.id,
                key=upload.s3_key,
                size=round(upload.size / 1024, 2),
                date_added=upload.date_added.isoformat(),
                sourcename=upload.source_filename,
                filename=upload.filename,
                author=upload.author,
                language=upload.language,
                file_type=upload.file_type,
                status=upload.status
            ))

        return FileListResponse(success=True, files=files)
    except Exception as e:
        return FileListResponse(success=False, error=str(e))


# 1. Request arrives → FastAPI sees Depends(get_db)
# 2. get_db() called → Gets session from connection pool  
# 3. yield session → Session passed to route function
# 4. Route executes → Uses session for database operations
# 5. Route finishes → Control returns to get_db()
# 6. finally block → session.close() called
# 7. Session returned to pool → Ready for next request
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(""),
    authors: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_db)
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
        metadata = Upload(
            id=file_id,
            filename=filename.strip(),
            author=authors.strip(),
            language=language,
            size=file_size,
            file_type=file_type,
            source_filename=source_filename,
            pages=0,
            status=0,  # 0: uploaded not processed, 1: processed
            s3_key=file_s3_key
            # date_added is auto-generated by Python
        )
        
        # print(metadata.model_dump())
        # PHASE 1: Prepare database transaction (don't commit yet) for file metadata
        session.add(metadata)
        session.flush()  # Validates but doesn't commit

        try:
            # PHASE 2: Upload to S3
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

            # Both operations are successful -> commit DB transaction
            session.commit()
        
            return RedirectResponse(url=f"/?message=File {file_s3_key} uploaded successfully&message_type=success", status_code=303)
        
        except Exception as s3_error:
            # If S3 upload fails, rollback DB transaction
            session.rollback()
            raise Exception(f"S3 upload failed: {str(s3_error)}")
        
    except Exception as e:
        session.rollback()
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
async def delete_file(s3_key: str, session: Session = Depends(get_db)):
    """Delete a file from S3 and remove metadata from lightsail mysql"""

    try:
        # Phase 1: Delete metadata from mysql
        statement = select(Upload).where(Upload.s3_key == s3_key)
        upload_record = session.exec(statement).first()
        if upload_record:
            session.delete(upload_record)
            session.flush()
        
        # Phase 2: Delete file from s3
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)

        # commit Mysql changes after s3 deletion success
        if upload_record:
            session.commit()
            return RedirectResponse(url=f"/?message=File {s3_key} deleted successfully&message_type=success", status_code=303)
        else:
            return RedirectResponse(url=f"/?message=File {s3_key} deleted from S3 (no metadata found)&message_type=success", status_code=303)
    
    except Exception as e:
        session.rollback()
        return RedirectResponse(url=f"/?message=ERROR DELETING FILE: {str(e)}&message_type=error", status_code=303)

# ====== Health Check ======
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=8000, reload=True) 