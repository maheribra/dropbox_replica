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
    try:
        db = get_database()
        blob_service = get_blob_client()
        
        # Check if services are available
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        if blob_service is None:
            raise HTTPException(status_code=500, detail="Blob storage connection unavailable")

        # 1. Verify destination directory exists and belongs to user
        try:
            dir_oid = ObjectId(directory_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid directory ID")
        
        dest_dir = db.directories.find_one({"_id": dir_oid, "owner_id": user_id})
        if not dest_dir:
            raise HTTPException(status_code=404, detail="Target directory not found")

        # 2. Process file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        
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
        try:
            container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
            container.upload_blob(blob_path, content, overwrite=True)
        except Exception as blob_error:
            raise HTTPException(status_code=500, detail=f"Blob upload failed: {str(blob_error)}")

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

    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@router.post("/upload/overwrite")
async def overwrite_file(
    file_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Overwrites an existing file record and its blob storage."""
    try:
        db = get_database()
        blob_service = get_blob_client()

        try:
            file_oid = ObjectId(file_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid file ID")

        existing = db.files.find_one({"_id": file_oid, "owner_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Original file not found")

        content = await file.read()
        
        # Update Storage
        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        container.upload_blob(existing["blob_url"], content, overwrite=True)

        # Update DB
        db.files.update_one(
            {"_id": file_oid},
            {"$set": {
                "file_hash": calculate_hash(content),
                "file_size": len(content),
                "updated_at": datetime.now()
            }}
        )
        return {"message": "File updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overwrite error: {str(e)}")

@router.get("/download")
async def download_file(file_id: str, user_id: str):
    """Streams file from Azurite. Supports shared file access."""
    try:
        db = get_database()
        blob_service = get_blob_client()
        
        try:
            file_oid = ObjectId(file_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid file ID")
        
        file_data = db.files.find_one({"_id": file_oid})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")

        # Access Control: Owner or Shared User
        if file_data["owner_id"] != user_id:
            has_share = db.shares.find_one({"file_id": file_id, "shared_with_id": user_id})
            if not has_share:
                raise HTTPException(status_code=403, detail="Access denied")

        container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        blob = container.download_blob(file_data["blob_url"])
        
        return StreamingResponse(
            io.BytesIO(blob.readall()),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_data['name']}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Download failed")

@router.delete("/delete")
async def delete_file(file_id: str, user_id: str):
    """Deletes file from storage and clears associated metadata/shares."""
    try:
        db = get_database()
        blob_service = get_blob_client()
        
        try:
            file_oid = ObjectId(file_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid file ID")
        
        file_data = db.files.find_one({"_id": file_oid, "owner_id": user_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")

        try:
            # Delete Blob
            container = blob_service.get_container_client(BLOB_CONTAINER_NAME)
            container.delete_blob(file_data["blob_url"])
        except:
            pass  # Continue even if blob is already gone
        
        # Cleanup DB
        db.files.delete_one({"_id": file_oid})
        db.shares.delete_many({"file_id": file_id})
        
        return {"message": "File removed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")

@router.get("/duplicates/directory")
async def find_duplicates_in_directory(directory_id: str, user_id: str):
    """
    Identifies duplicate files in the current directory only (Group 3).
    """
    try:
        db = get_database()
        
        try:
            dir_oid = ObjectId(directory_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid directory ID")
        
        # Find all files in this directory
        files = list(db.files.find({"directory_id": directory_id, "owner_id": user_id}))
        
        # Group by hash
        hash_groups = {}
        for file in files:
            file_hash = file.get("file_hash")
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(file)
        
        # Filter to only duplicates (hash appears more than once)
        duplicates = []
        for file_hash, file_list in hash_groups.items():
            if len(file_list) > 1:
                duplicates.append({
                    "hash": file_hash,
                    "files": [
                        {
                            "id": str(f["_id"]),
                            "name": f["name"],
                            "size": f.get("file_size", 0),
                            "path": db.directories.find_one({"_id": ObjectId(f["directory_id"])}, {"path": 1}).get("path", "/")
                        }
                        for f in file_list
                    ]
                })
        
        return {"duplicates": duplicates}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate check error: {str(e)}")

@router.get("/duplicates/all")
async def find_all_duplicates(user_id: str):
    """
    Identifies duplicate files across the entire account (Group 4).
    Uses aggregation for better performance than manual looping.
    """
    try:
        db = get_database()
        
        # Find all files for this user
        files = list(db.files.find({"owner_id": user_id}))
        
        # Group by hash
        hash_groups = {}
        for file in files:
            file_hash = file.get("file_hash")
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(file)
        
        # Filter to only duplicates (hash appears more than once)
        duplicates = []
        total_duplicates = 0
        for file_hash, file_list in hash_groups.items():
            if len(file_list) > 1:
                total_duplicates += len(file_list) - 1  # Count duplicates, not originals
                duplicates.append({
                    "hash": file_hash,
                    "files": [
                        {
                            "id": str(f["_id"]),
                            "name": f["name"],
                            "size": f.get("file_size", 0),
                            "path": db.directories.find_one({"_id": ObjectId(f["directory_id"])}, {"path": 1}).get("path", "/")
                        }
                        for f in file_list
                    ]
                })
        
        return {
            "duplicates": duplicates,
            "total_duplicate_count": total_duplicates
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate check error: {str(e)}")