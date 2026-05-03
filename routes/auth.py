from fastapi import APIRouter, Request, HTTPException, status
from datetime import datetime
from bson import ObjectId
from config import get_database

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
async def login(request: Request):
    """
    Authenticates user from Firebase data and initializes 
    new users with a root directory.
    """
    try:
        data = await request.json()
        uid = data.get("uid")
        email = data.get("email")
        display_name = data.get("displayName")
        
        if not uid or not email:
            raise HTTPException(status_code=400, detail="Missing required user data")

        db = get_database()
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        users_col = db["users"]
        dirs_col = db["directories"]
        
        # Check if this user already exists in our system
        user = users_col.find_one({"uid": uid})
        
        if user:
            return {
                "user_id": str(user["_id"]),
                "email": user["email"],
                "display_name": user["display_name"],
                "root_directory_id": user.get("root_directory_id")
            }
        
        # Initialize New User
        new_user_doc = {
            "uid": uid,
            "email": email,
            "display_name": display_name,
            "created_at": datetime.now(),
            "root_directory_id": None # Placeholder
        }
        user_result = users_col.insert_one(new_user_doc)
        new_user_id = str(user_result.inserted_id)
        
        # Requirement: Every new user needs a root directory (/)
        root_dir_doc = {
            "name": "root",
            "path": "/",
            "parent_id": None,
            "owner_id": new_user_id,
            "created_at": datetime.now(),
            "is_root": True
        }
        root_result = dirs_col.insert_one(root_dir_doc)
        root_id = str(root_result.inserted_id)
        
        # Link the root directory back to the user
        users_col.update_one(
            {"_id": ObjectId(new_user_id)},
            {"$set": {"root_directory_id": root_id}}
        )
        
        return {
            "user_id": new_user_id,
            "email": email,
            "display_name": display_name,
            "root_directory_id": root_id
        }
    
    except Exception as e:
        # Standardize error response
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@router.get("/user")
async def get_current_user(user_id: str):
    """Retrieves specific user details from MongoDB."""
    db = get_database()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection unavailable")
    
    try:
        user = db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User record not found")
        
        return {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "display_name": user["display_name"],
            "root_directory_id": user.get("root_directory_id")
        }
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

@router.post("/logout")
async def logout():
    """Placeholder for server-side logout logic if needed."""
    return {"message": "Session terminated"}