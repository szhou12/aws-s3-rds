# FastAPI S3 File Manager

This is a FastAPI version of the Flask S3 file manager application.

## Key Differences from Flask Version

### 1. **Framework & Dependencies**
- **FastAPI** instead of Flask
- **Uvicorn** ASGI server instead of Flask dev server
- **Pydantic** models for data validation
- **Jinja2** for templating (explicit dependency)

### 2. **File Upload Handling**
- Uses `UploadFile` type with automatic file size calculation
- Form data handled with `Form()` dependencies
- Proper async/await support

### 3. **Message System**
- Query parameters instead of Flask flash messages
- Messages passed via URL redirects with `message` and `message_type` parameters

### 4. **Response Types**
- **StreamingResponse** for file downloads
- **RedirectResponse** for form submissions
- **Pydantic models** for API responses

### 5. **File Size Calculation**
The FastAPI version includes a robust file size calculation function:
```python
def calculate_file_size(file: UploadFile) -> int:
    """Calculate file size using seek and tell method"""
    file.file.seek(0, 2)  # Seek to end of file
    file_size = file.file.tell()  # Get current position (file size)
    file.file.seek(0)  # Reset to beginning for upload
    return file_size
```

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements_fastapi.txt
```

### 2. Configure AWS
Set up your AWS credentials and update the S3 bucket name in `app_fastapi.py`:
```python
AWS_S3_BUCKET = 'your-bucket-name'  # Update this!
```

### 3. Run the Application
```bash
# Development mode with auto-reload
python app_fastapi.py

# Or using uvicorn directly
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the Application
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/upload` | POST | Upload file with metadata |
| `/list-files` | GET | List all files (JSON API) |
| `/download/{filename}` | GET | Download a file |
| `/delete/{filename}` | GET | Delete a file |
| `/health` | GET | Health check |

## Features

✅ **File Upload** with metadata (filename, authors, language)  
✅ **File Download** with original filename preservation  
✅ **File Deletion** with confirmation  
✅ **File Listing** with size and modification date  
✅ **File Size Calculation** using efficient seek/tell method  
✅ **AWS S3 Integration** with metadata storage  
✅ **Input Validation** with Pydantic models  
✅ **Error Handling** with user-friendly messages  
✅ **Auto-generated API Documentation**  

## Production Deployment

For production, use a production ASGI server:

```bash
# Using Gunicorn with Uvicorn workers
gunicorn app_fastapi:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or using Uvicorn directly
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --workers 4
```

## Advantages of FastAPI Version

1. **Better Performance** - Async support and faster than Flask
2. **Automatic API Documentation** - Swagger UI and ReDoc included
3. **Type Safety** - Pydantic models provide validation and IDE support
4. **Modern Python** - Uses modern Python type hints and async/await
5. **Better Error Handling** - Built-in validation and error responses
6. **Production Ready** - Designed for production with ASGI servers 