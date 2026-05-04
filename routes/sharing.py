from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from bson import ObjectId
from config import get_database

router = APIRouter(prefix="/api/sharing", tags=["sharing"])

@router.post("/share")
async def share_file(request: Request):
    """
    Shares a file (read-only) with another user by email.
    Creates a share record linking the file to the recipient.
    """
    try:
        data = await request.json()
        file_id = data.get("file_id")
        owner_id = data.get("owner_id")
        shared_with_email = data.get("shared_with_email")
        
        if not all([file_id, owner_id, shared_with_email]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        try:
            file_oid = ObjectId(file_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid file ID")
        
        # Verify file exists and belongs to owner
        file_doc = db.files.find_one({"_id": file_oid, "owner_id": owner_id})
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Find the user to share with by email
        shared_with_user = db.users.find_one({"email": shared_with_email})
        if not shared_with_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        shared_with_id = str(shared_with_user["_id"])
        
        # Prevent sharing with self
        if owner_id == shared_with_id:
            raise HTTPException(status_code=400, detail="Cannot share with yourself")
        
        # Check if already shared
        existing_share = db.shares.find_one({
            "file_id": file_id,
            "shared_with_id": shared_with_id
        })
        if existing_share:
            raise HTTPException(status_code=400, detail="Already shared with this user")
        
        # Create share record
        share_doc = {
            "file_id": file_id,
            "file_name": file_doc["name"],
            "owner_id": owner_id,
            "owner_email": db.users.find_one({"_id": ObjectId(owner_id)})["email"],
            "shared_with_id": shared_with_id,
            "shared_with_email": shared_with_email,
            "created_at": datetime.now(),
            "shared_at": datetime.now()
        }
        
        result = db.shares.insert_one(share_doc)
        
        return {
            "share_id": str(result.inserted_id),
            "message": f"File shared with {shared_with_email}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Share error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Share error: {str(e)}")


@router.get("/shared-with-me")
async def get_shared_with_me(user_id: str):
    """
    Retrieves all files that have been shared with the current user.
    Returns a list of shared files with owner information.
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        # Find all shares where this user is the recipient
        shares = list(db.shares.find({"shared_with_id": user_id}))
        
        shared_files = []
        for share in shares:
            shared_files.append({
                "file_id": share["file_id"],
                "file_name": share.get("file_name", "Unknown"),
                "owner_email": share.get("owner_email", "Unknown"),
                "shared_at": share["shared_at"].isoformat() if share.get("shared_at") else None
            })
        
        return {"shared_files": shared_files}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get shared error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving shares: {str(e)}")


@router.get("/my-shares")
async def get_my_shares(user_id: str):
    """
    Retrieves all files that the current user has shared with others.
    Returns a list of shares with recipient information.
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        # Find all shares where this user is the owner
        shares = list(db.shares.find({"owner_id": user_id}))
        
        my_shares = []
        for share in shares:
            my_shares.append({
                "file_id": share["file_id"],
                "file_name": share.get("file_name", "Unknown"),
                "shared_with_email": share.get("shared_with_email", "Unknown"),
                "shared_at": share["shared_at"].isoformat() if share.get("shared_at") else None
            })
        
        return {"my_shares": my_shares}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get my shares error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving your shares: {str(e)}")


@router.delete("/unshare")
async def unshare_file(request: Request):
    """
    Removes a file share.
    The owner can remove any share, or a recipient can unshare from themselves.
    """
    try:
        data = await request.json()
        share_id = data.get("share_id")
        user_id = data.get("user_id")
        
        if not share_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        try:
            share_oid = ObjectId(share_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid share ID")
        
        share = db.shares.find_one({"_id": share_oid})
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")
        
        # Only owner or recipient can unshare
        if share["owner_id"] != user_id and share["shared_with_id"] != user_id:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        db.shares.delete_one({"_id": share_oid})
        
        return {"message": "Share removed"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unshare error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unshare error: {str(e)}")