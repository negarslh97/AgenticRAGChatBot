from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.api.dependencies import get_current_user
from app.domain.entities import User
import os
import uuid
from pathlib import Path

router = APIRouter()

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/admin/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a file for processing."""
    
    # Check if user is admin
    if current_user.role not in ["admin", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload files")
    
    # Check file extension
    allowed_extensions = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".txt"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_size = 0
    
    # Read file to check size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # Reset file pointer
    
    if file_size > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = Path(original_filename).suffix.lower()
    new_filename = f"{file_id}{file_extension}"
    
    # Save file
    file_path = UPLOAD_DIR / new_filename
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create processing job (you can extend this with a background task)
    processing_job = {
        "id": file_id,
        "filename": original_filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "uploaded_by": str(current_user.id),
        "status": "uploaded",
        "created_at": str(file_path.stat().st_ctime)
    }
    
    # Here you would typically save this to a database
    # and trigger a background processing job
    
    return {
        "success": True,
        "file_id": file_id,
        "filename": original_filename,
        "file_size": file_size,
        "message": "File uploaded successfully. Processing will begin shortly."
    }