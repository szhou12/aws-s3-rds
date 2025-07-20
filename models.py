from typing import Optional
from datetime import datetime
from pydantic import BaseModel

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

class Upload(BaseModel):
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