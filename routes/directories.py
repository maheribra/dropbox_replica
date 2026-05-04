from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from bson import ObjectId
from config import get_database

router = APIRouter(prefix="/api/directories", tags=["directories"])

@router.post("/create")
async def create_directory(request: Request):
    """Creates a new subdirectory and calculates its hierarchical path."""
    try:
        data = await request.json()
        parent_id = data.get("parent_directory_id")
        dir_name = data.get("directory_name")
        user_id = data.get("user_id")
        
        if not all([parent_id, dir_name, user_id]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        db = get_database()
        
        # Verify parent exists and belongs to user
        try:
            parent_oid = ObjectId(parent_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid parent directory ID")
        
        parent_dir = db.directories.find_one({"_id": parent_oid, "owner_id": user_id})
        if not parent_dir:
            raise HTTPException(status_code=404, detail="Parent directory not found")
        
        # Prevent duplicate names in the same folder
        if db.directories.find_one({"parent_id": parent_oid, "name": dir_name}):
            raise HTTPException(status_code=400, detail="Directory already exists")
        
        # Construct hierarchical path
        parent_path = parent_dir.get("path", "/")
        if parent_path == "/":
            new_path = f"/{dir_name}"
        else:
            new_path = f"{parent_path}/{dir_name}"
        
        new_dir = {
            "name": dir_name,
            "path": new_path,
            "parent_id": parent_oid,
            "owner_id": user_id,
            "created_at": datetime.now(),
            "is_root": False
        }
        
        result = db.directories.insert_one(new_dir)
        return {
            "directory_id": str(result.inserted_id),
            "name": dir_name,
            "path": new_path
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete")
async def delete_directory(request: Request):
    """Deletes a directory only if it is empty (no files or subfolders)."""
    try:
        data = await request.json()
        dir_id = data.get("directory_id")
        user_id = data.get("user_id")
        
        if not dir_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        db = get_database()
        
        try:
            dir_oid = ObjectId(dir_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid directory ID")
        
        target = db.directories.find_one({"_id": dir_oid, "owner_id": user_id})
        
        if not target:
            raise HTTPException(status_code=404, detail="Directory not found")
        if target.get("is_root"):
            raise HTTPException(status_code=400, detail="Cannot delete root directory")
        
        # Group 3 Check: Ensure directory is empty
        has_subdirs = db.directories.find_one({"parent_id": dir_oid})
        has_files = db.files.find_one({"directory_id": dir_oid})
        
        if has_subdirs or has_files:
            raise HTTPException(status_code=400, detail="Directory is not empty")
        
        db.directories.delete_one({"_id": dir_oid})
        return {"message": "Directory deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contents")
async def get_directory_contents(directory_id: str, user_id: str):
    """Lists all files and subfolders within a directory."""
    db = get_database()
    
    current_dir = db.directories.find_one({"_id": ObjectId(directory_id), "owner_id": user_id})
    if not current_dir:
        raise HTTPException(status_code=404, detail="Directory not found")

    # Fetch and format subdirectories
    subdirs = [{
        "id": str(d["_id"]),
        "name": d["name"],
        "path": d["path"],
        "type": "directory"
    } for d in db.directories.find({"parent_id": directory_id}).sort("name", 1)]

    # Fetch and format files
    files = [{
        "id": str(f["_id"]),
        "name": f["name"],
        "size": f.get("file_size", 0),
        "created_at": f["created_at"].isoformat(),
        "type": "file"
    } for f in db.files.find({"directory_id": directory_id}).sort("name", 1)]

    return {
        "current_directory": {
            "id": str(current_dir["_id"]),
            "name": current_dir["name"],
            "path": current_dir["path"],
            "is_root": current_dir.get("is_root", False)
        },
        "subdirectories": subdirs,
        "files": files,
        "parent_available": not current_dir.get("is_root", False)
    }

@router.post("/navigate")
async def navigate_directory(request: Request):
    """Handles logic for moving 'up' to parent or 'into' a child folder."""
    data = await request.json()
    curr_id = data.get("current_directory_id")
    direction = data.get("direction")
    user_id = data.get("user_id")

    db = get_database()
    current = db.directories.find_one({"_id": ObjectId(curr_id), "owner_id": user_id})
    if not current:
        raise HTTPException(status_code=404, detail="Directory context lost")

    # Group 2: Navigation Logic
    if direction == "up":
        if current.get("is_root"):
            raise HTTPException(status_code=400, detail="Already at root")
        
        parent = db.directories.find_one({"_id": ObjectId(current["parent_id"])})
        return {"new_directory_id": str(parent["_id"]), "path": parent["path"]}

    elif direction == "into":
        target_id = data.get("target_directory_id")
        target = db.directories.find_one({"_id": ObjectId(target_id), "parent_id": curr_id})
        if not target:
            raise HTTPException(status_code=404, detail="Subdirectory not found")
            
        return {"new_directory_id": str(target["_id"]), "path": target["path"]}
    
    raise HTTPException(status_code=400, detail="Invalid navigation direction")