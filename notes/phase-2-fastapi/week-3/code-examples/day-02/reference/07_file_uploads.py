"""
File Uploads - Complete Guide
==============================

Topics covered:
1. How file uploads work (backend view)
2. Single file upload
3. File vs UploadFile comparison
4. Multiple file uploads
5. File + metadata (form fields)
6. File type validation
7. File size validation
8. Saving files to disk
9. Best practices and security

Run: uvicorn 07_file_uploads:app --reload
Test: http://localhost:8000/docs
Test with client: Open clients/test_uploads.html in browser

Important: Requires python-multipart
Install: pip install python-multipart
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import List
import shutil
from pathlib import Path
import os

app = FastAPI(
    title="File Uploads Guide",
    description="Complete guide to handling file uploads in FastAPI",
    version="1.0.0"
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# =============================================================================
# 1. HOW FILE UPLOADS WORK (Backend View)
# =============================================================================
"""
File uploads use multipart/form-data encoding.

Process:
1. Client sends request with Content-Type: multipart/form-data
2. Each file becomes a SEPARATE PART of the request body
3. FastAPI parses the stream using python-multipart
4. Files are exposed as UploadFile objects

UploadFile provides:
- filename: Original client filename
- content_type: MIME type sent by client
- file: Underlying file-like object
- read(): Async read
- seek(): Reset pointer
- close(): Cleanup resources

Important:
- File uploads are always REQUEST BODY
- Must be explicitly marked using File(...)
- Can be combined with Form() for metadata
"""


# =============================================================================
# 2. SINGLE FILE UPLOAD
# =============================================================================

@app.post("/upload/single")
async def upload_single_file(
    file: UploadFile = File(...)
):
    """
    Upload a single file.
    
    UploadFile gives you:
    - filename: Original filename from client
    - content_type: MIME type
    - file: File-like object for reading
    
    Test with curl:
    curl -X POST http://localhost:8000/upload/single \
      -F "file=@/path/to/your/file.txt"
    
    Or use the interactive docs at /docs
    """
    # Read file contents
    contents = await file.read()
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "message": "File uploaded successfully"
    }


@app.post("/upload/save")
async def upload_and_save(
    file: UploadFile = File(...)
):
    """
    Upload and save file to disk.
    
    This is more realistic - you usually want to save files.
    
    Security note: In real apps, you should:
    - Sanitize filenames
    - Generate server-side filenames
    - Check file types
    - Scan for malware
    """
    # Create safe filename (in real app, use UUID or hash)
    file_path = UPLOAD_DIR / file.filename
    
    try:
        # Save file using shutil.copyfileobj (efficient streaming)
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "filename": file.filename,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "message": "File saved successfully"
        }
    
    finally:
        await file.close()


# =============================================================================
# 3. File vs UploadFile COMPARISON
# =============================================================================

@app.post("/upload/bytes")
async def upload_bytes(
    file: bytes = File(...)
):
    """
    Upload using bytes (File).
    
    Behavior:
    - Entire file loaded into memory
    - Simple but DANGEROUS for large files
    - Can cause memory issues
    
    Use only when:
    - Files are very small (<1MB)
    - You fully trust the client
    - You need the entire file in memory at once
    
    For most cases, use UploadFile instead!
    """
    return {
        "size": len(file),
        "type": "bytes",
        "warning": "Entire file loaded into memory"
    }


@app.post("/upload/uploadfile")
async def upload_uploadfile(
    file: UploadFile = File(...)
):
    """
    Upload using UploadFile (RECOMMENDED).
    
    Behavior:
    - Stored in memory up to a limit (typically 1MB)
    - Automatically spills to disk for larger files
    - Much lower memory usage
    - Can be read in chunks
    
    Backend rule: ALWAYS use UploadFile unless you have a strong reason not to.
    """
    contents = await file.read()
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "type": "UploadFile",
        "note": "Efficient memory usage"
    }


# =============================================================================
# 4. MULTIPLE FILE UPLOADS
# =============================================================================

@app.post("/upload/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple files at once.
    
    How it works:
    - HTML input uses multiple attribute
    - Each file is sent as separate part
    - FastAPI collects them into a list
    
    Common use cases:
    - Image galleries
    - Bulk document uploads
    - Photo albums
    
    Test with curl:
    curl -X POST http://localhost:8000/upload/multiple \
      -F "files=@file1.txt" \
      -F "files=@file2.txt" \
      -F "files=@file3.txt"
    """
    file_info = []
    
    for file in files:
        # Read each file
        contents = await file.read()
        
        file_info.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents)
        })
        
        # Reset file pointer for potential re-reading
        await file.seek(0)
    
    return {
        "count": len(file_info),
        "files": file_info,
        "message": f"Uploaded {len(file_info)} files successfully"
    }


@app.post("/upload/multiple-save")
async def upload_multiple_and_save(
    files: List[UploadFile] = File(...)
):
    """
    Upload and save multiple files.
    
    Real-world pattern for bulk uploads.
    """
    saved_files = []
    
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            saved_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
        
        finally:
            await file.close()
    
    return {
        "count": len(saved_files),
        "files": saved_files,
        "message": "All files saved successfully"
    }


# =============================================================================
# 5. FILE + METADATA (Form Fields)
# =============================================================================

@app.post("/upload/with-metadata")
async def upload_with_metadata(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    tags: str | None = Form(None)  # Comma-separated tags
):
    """
    Upload file with metadata.
    
    Important:
    - File + form fields must use multipart/form-data
    - File() and Form() can coexist
    - Very common in real applications
    
    Typical use case:
    - Upload profile picture + username
    - Upload document + title + description
    - Upload image + tags + category
    
    Test with curl:
    curl -X POST http://localhost:8000/upload/with-metadata \
      -F "file=@image.jpg" \
      -F "title=My Image" \
      -F "description=A beautiful sunset" \
      -F "tags=nature,sunset,photography"
    """
    contents = await file.read()
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    return {
        "file": {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents)
        },
        "metadata": {
            "title": title,
            "description": description,
            "tags": tag_list
        },
        "message": "File and metadata uploaded successfully"
    }


@app.post("/upload/profile")
async def upload_profile(
    profile_picture: UploadFile = File(...),
    username: str = Form(...),
    bio: str | None = Form(None)
):
    """
    Real-world example: Profile picture upload.
    
    Common in user profile updates.
    """
    contents = await profile_picture.read()
    
    return {
        "profile": {
            "username": username,
            "bio": bio,
            "picture": {
                "filename": profile_picture.filename,
                "size": len(contents)
            }
        },
        "message": "Profile updated successfully"
    }


# =============================================================================
# 6. FILE TYPE VALIDATION
# =============================================================================

# Allowed file types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp"
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}


@app.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...)
):
    """
    Upload image with type validation.
    
    Validates content_type before processing.
    
    Important:
    - content_type is CLIENT-PROVIDED
    - Never trust it blindly
    - For high-security: inspect file headers
    - Use libraries like python-magic for real type detection
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    contents = await file.read()
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "message": "Image uploaded successfully"
    }


@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...)
):
    """
    Upload document with type validation.
    """
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: PDF, DOC, DOCX"
        )
    
    contents = await file.read()
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "message": "Document uploaded successfully"
    }


# =============================================================================
# 7. FILE SIZE VALIDATION
# =============================================================================

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@app.post("/upload/size-limited")
async def upload_size_limited(
    file: UploadFile = File(...)
):
    """
    Upload with file size limit.
    
    This checks size after reading the file.
    For production, also set limit at reverse proxy (NGINX).
    """
    contents = await file.read()
    
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f} MB"
        )
    
    return {
        "filename": file.filename,
        "size": len(contents),
        "max_size": MAX_FILE_SIZE,
        "message": "File within size limit"
    }


@app.post("/upload/validated")
async def upload_fully_validated(
    file: UploadFile = File(...)
):
    """
    Upload with comprehensive validation.
    
    Validates:
    - File type
    - File size
    - Filename (basic sanitization)
    
    This is closer to production-ready code.
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only images allowed (JPEG, PNG, GIF, WebP)"
        )
    
    # Read and validate size
    contents = await file.read()
    
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_FILE_SIZE / (1024*1024):.1f} MB)"
        )
    
    # Validate filename (basic)
    if not file.filename or ".." in file.filename or "/" in file.filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
        "validation": "passed",
        "message": "File uploaded and validated successfully"
    }


# =============================================================================
# 8. REAL-WORLD PATTERNS
# =============================================================================

@app.post("/upload/product-image")
async def upload_product_image(
    image: UploadFile = File(...),
    product_id: int = Form(...),
    alt_text: str = Form(...),
    is_primary: bool = Form(False)
):
    """
    Real-world: Upload product image with metadata.
    
    Common in e-commerce applications.
    """
    # Validate image type
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    contents = await image.read()
    
    # Validate size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large")
    
    # In real app: save to cloud storage (S3), resize, etc.
    
    return {
        "product_id": product_id,
        "image": {
            "filename": image.filename,
            "size": len(contents),
            "alt_text": alt_text,
            "is_primary": is_primary
        },
        "message": "Product image uploaded successfully"
    }


@app.post("/upload/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    user_id: int = Form(...)
):
    """
    Real-world: Upload user avatar.
    
    Typical flow:
    1. Validate image type and size
    2. Generate unique filename (UUID)
    3. Resize image (thumbnail, medium, large)
    4. Upload to cloud storage
    5. Update user record with image URL
    """
    # Validation
    if avatar.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    contents = await avatar.read()
    
    if len(contents) > 2 * 1024 * 1024:  # 2MB for avatars
        raise HTTPException(status_code=400, detail="Avatar too large (max 2MB)")
    
    # Generate unique filename
    import uuid
    extension = avatar.filename.split(".")[-1] if "." in avatar.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        buffer.write(contents)
    
    return {
        "user_id": user_id,
        "avatar": {
            "original_filename": avatar.filename,
            "stored_filename": unique_filename,
            "url": f"/uploads/{unique_filename}",
            "size": len(contents)
        },
        "message": "Avatar uploaded successfully"
    }


# =============================================================================
# 9. TESTING INTERFACE
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    HTML interface for testing file uploads.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload Testing</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            form { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            label { display: block; margin: 10px 0 5px 0; font-weight: bold; }
            input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .output { background: #fff; padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            pre { background: #f8f8f8; padding: 10px; overflow-x: auto; }
            .preview { max-width: 200px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>File Upload Testing Interface</h1>
        
        <h2>Single File Upload</h2>
        <form id="singleForm">
            <label>Select File:</label>
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
        </form>
        
        <h2>Multiple Files Upload</h2>
        <form id="multipleForm">
            <label>Select Files:</label>
            <input type="file" name="files" multiple required>
            <button type="submit">Upload All</button>
        </form>
        
        <h2>File with Metadata</h2>
        <form id="metadataForm">
            <label>Select File:</label>
            <input type="file" name="file" required>
            
            <label>Title:</label>
            <input type="text" name="title" required>
            
            <label>Description:</label>
            <textarea name="description" rows="3"></textarea>
            
            <label>Tags (comma-separated):</label>
            <input type="text" name="tags" placeholder="tag1, tag2, tag3">
            
            <button type="submit">Upload with Metadata</button>
        </form>
        
        <h2>Image Upload (Type Validated)</h2>
        <form id="imageForm">
            <label>Select Image:</label>
            <input type="file" name="file" accept="image/*" required>
            <div id="imagePreview"></div>
            <button type="submit">Upload Image</button>
        </form>
        
        <div class="output" id="output">
            <p>Upload a file above to see the response</p>
        </div>
        
        <script>
            const output = document.getElementById('output');
            
            // Single file upload
            document.getElementById('singleForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/upload/single', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Upload Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
            
            // Multiple files upload
            document.getElementById('multipleForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/upload/multiple', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Multiple Upload Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
            
            // File with metadata
            document.getElementById('metadataForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/upload/with-metadata', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Metadata Upload Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
            
            // Image upload with preview
            const imageInput = document.querySelector('#imageForm input[type="file"]');
            const imagePreview = document.getElementById('imagePreview');
            
            imageInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        imagePreview.innerHTML = `<img src="${e.target.result}" class="preview">`;
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            document.getElementById('imageForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/upload/image', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Image Upload Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
        </script>
    </body>
    </html>
    """


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing File Uploads:

1. Using Browser:
   - Visit http://localhost:8000/
   - Use built-in file upload forms
   - Preview images before upload
   - See responses immediately

2. Using curl:
   # Single file
   curl -X POST http://localhost:8000/upload/single \
     -F "file=@/path/to/file.txt"
   
   # Multiple files
   curl -X POST http://localhost:8000/upload/multiple \
     -F "files=@file1.txt" \
     -F "files=@file2.txt"
   
   # File with metadata
   curl -X POST http://localhost:8000/upload/with-metadata \
     -F "file=@image.jpg" \
     -F "title=My Image" \
     -F "description=Beautiful sunset"

3. Using httpie:
   http --form POST localhost:8000/upload/single \
     file@/path/to/file.txt

4. Using Python requests:
   with open('file.txt', 'rb') as f:
       files = {'file': f}
       response = requests.post(
           'http://localhost:8000/upload/single',
           files=files
       )

Common Backend Mistakes:
- Loading large files into memory (use UploadFile)
- Trusting client-provided filename
- Trusting MIME type without validation
- Not setting file size limits
- Blocking I/O in request handlers
- Not sanitizing filenames

Backend Best Practices:
- Always use UploadFile (not bytes)
- Validate file size and type
- Generate server-side filenames (UUID)
- Set upload size limit at reverse proxy
- Offload storage to S3 or similar
- Scan files for malware in production
- Never trust client-provided metadata
- Use streaming for large files
- Clean up temporary files

Security Checklist:
☐ Validate file type (don't trust content_type)
☐ Validate file size
☐ Sanitize/generate filenames
☐ Set maximum upload size
☐ Scan for malware
☐ Use cloud storage for scale
☐ Never execute uploaded files
☐ Restrict file access
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
