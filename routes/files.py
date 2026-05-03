from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from datetime import datetime
from bson import ObjectId
import hashlib
import io

from config import get_database, get_blob_client, BLOB_CONTAINER_NAME

router = APIRouter(prefix="/api/files", tags=["files"])

def calculate_hash(content: bytes) -> str:
    """Computes SHA256 hash for duplicate detection."""
    return hashlib.sha256(content).hexdigest()

@router.post("/upload")
async def upload_file(
    directory_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Handles file uploads with duplicate name checking.
    If the file name exists, returns a status to prompt user for overwrite.
    """
    db = get_database()
    blob_service = get_blob_client()
    
    if not db or not blob_service:
        raise HTTPException(status_code=500, detail="External services unavailable")

    try:
        # 1. Verify destination directory exists and belongs to user
        dest_dir = db.directories.find_one({"_id": ObjectId(directory_id), "owner_id": user_id})
        if not dest_dir:
            raise HTTPException(status_code=404, detail="Target directory not found")

        # 2. Process file content
        content = await file.read()
        file_hash = calculate_hash(content)
        
        # 3. Collision Check: Does this filename exist in this folder?
        existing = db.files.find_one({
            "directory_id": directory_id,
            "name": file.filename,
            "owner_id": user_id
        })

        if existing:
            return {
                "status": "exists",
                "file_name": file.filename,
                "file_id": str(existing["_id"])
            }

        # 4. Storage: Upload to Azurite
        blob_path = f"{user_id}/{directory_id}/{file.filename}"
        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        container.upload_blob(blob_path, content, overwrite=True)

        # 5. DB: Register file record
        new_file = {
            "name": file.filename,
            "directory_id": directory_id,
            "owner_id": user_id,
            "blob_url": blob_path,
            "file_size": len(content),
            "file_hash": file_hash,
            "created_at": datetime.now()
        }
        
        result = db.files.insert_one(new_file)
        return {"file_id": str(result.inserted_id), "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/overwrite")
async def overwrite_file(
    file_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Overwrites an existing file record and its blob storage."""
    db = get_database()
    blob_service = get_blob_client()

    try:
        existing = db.files.find_one({"_id": ObjectId(file_id), "owner_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Original file not found")

        content = await file.read()
        
        # Update Storage
        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        container.upload_blob(existing["blob_url"], content, overwrite=True)

        # Update DB
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {
                "file_hash": calculate_hash(content),
                "file_size": len(content),
                "updated_at": datetime.now()
            }}
        )
        return {"message": "File updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def download_file(file_id: str, user_id: str):
    """Streams file from Azurite. Supports shared file access."""
    db = get_database()
    blob_service = get_blob_client()
    
    file_data = db.files.find_one({"_id": ObjectId(file_id)})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    # Access Control: Owner or Shared User
    if file_data["owner_id"] != user_id:
        has_share = db.shares.find_one({"file_id": file_id, "shared_with_id": user_id})
        if not has_share:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        blob = container.download_blob(file_data["blob_url"])
        
        return StreamingResponse(
            io.BytesIO(blob.readall()),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_data['name']}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Download failed")

@router.delete("/delete")
async def delete_file(file_id: str, user_id: str):
    """Deletes file from storage and clears associated metadata/shares."""
    db = get_database()
    blob_service = get_blob_client()
    
    file_data = db.files.find_one({"_id": ObjectId(file_id), "owner_id": user_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Delete Blob
        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        container.delete_blob(file_data["blob_url"])
        
        # Cleanup DB
        db.files.delete_one({"_id": ObjectId(file_id)})
        db.shares.delete_many({"file_id": file_id})
        
        return {"message": "File removed"}
    except Exception as e:
        # We proceed with DB deletion even if blob is already gone
        db.files.delete_one({"_id": ObjectId(file_id)})
        return {"message": "File metadata removed (storage already empty)"}

@router.get("/duplicates/all")
async def find_all_duplicates(user_id: str):
    """
    Identifies duplicate files across the entire account (Group 4).
    Uses aggregation for better performance than manual looping.
    """
    db = get_database()
    
    pipeline = [
        {"$match": {"owner_id": user_id}},
        {
            "$group": {
                "_id": "$file_hash",
                "count": {"$sum": 1},
                "files": {"$push": {"id": {"$toString": "$_id"}, "name": "$name", "dir": "$directory_id"}}
            }
        },
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = list(db.files.aggregate(pipeline))
    return {
        "total_groups": len(duplicates),
        "duplicates": duplicates
    }