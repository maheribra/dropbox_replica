from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    uid: str
    email: str
    display_name: str
    created_at: datetime
    root_directory_id: Optional[str] = None


class Directory(BaseModel):
    name: str
    path: str
    parent_id: Optional[str] = None
    owner_id: str
    created_at: datetime
    is_root: bool = False


class File(BaseModel):
    name: str
    directory_id: str
    owner_id: str
    blob_url: str
    file_size: int
    file_hash: str
    created_at: datetime
    uploaded_by: str


class Share(BaseModel):
    file_id: str
    owner_id: str
    shared_with_id: str
    shared_at: datetime
    is_read_only: bool = True


class ErrorResponse(BaseModel):
    error: str
    code: Optional[str] = None

if __name__ == "__main__":
    # Creating a dummy user
    test_user = User(
        uid="user_123",
        email="ibrahim@example.com",
        display_name="Sheikh Ibrahim",
        created_at=datetime.now()
    )

    print("--- Pydantic Model Test ---")
    print(f"User Object: {test_user}")
    print(f"User Email: {test_user.email}")
    
    print(f"Dictionary for DB: {test_user.model_dump()}")