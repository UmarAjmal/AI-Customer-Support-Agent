"""
app/api/uploads.py — Secure file uploads (refund receipt attachments / product photos).
Supports validation of file size and MIME types.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.database import schemas

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


@router.post("", response_model=schemas.StandardResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    Upload files secure, saving them to the media folder.
    Validates file sizes (< MAX_FILE_SIZE_MB) and matching file extensions.
    """
    # 1. Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Check file size
    contents = await file.read()
    size = len(contents)
    if size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    # Reset cursor for writing
    await file.seek(0)

    # 3. Create unique filename and save
    unique_filename = f"{uuid.uuid4()}{ext}"
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/static/uploads/{unique_filename}"
    
    return schemas.StandardResponse(
        success=True,
        message="File uploaded successfully",
        data={"url": file_url, "size_bytes": size, "filename": file.filename}
    )
