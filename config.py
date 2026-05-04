from pymongo import MongoClient
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "dropbox_replica")

database = None
try:
    mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    # Test connection
    mongo_client.admin.command('ping')
    database = mongo_client[DATABASE_NAME]
    print("✅ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    database = None

# Azure / Azurite setup
AZURE_STORAGE_CONNECTION_STRING = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

BLOB_CONTAINER_NAME = "dropbox-files"
blob_service_client = None

try:
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

    # Check if container exists; if not, create it
    try:
        if not container_client.exists():
            container_client.create_container()
            print(f"✅ Container '{BLOB_CONTAINER_NAME}' created")
        else:
            print(f"✅ Container '{BLOB_CONTAINER_NAME}' already exists")
    except Exception as e:
        print(f"⚠️ Container check failed: {e}")

except Exception as e:
    print(f"❌ Azurite connection failed: {e}")
    blob_service_client = None


def get_database():
    """Returns MongoDB database connection"""
    if database is None:
        print("⚠️ Warning: Database is not initialized")
    return database


def get_blob_client():
    """Returns Azure Blob Service Client"""
    if blob_service_client is None:
        print("⚠️ Warning: Blob service client is not initialized")
    return blob_service_client


if __name__ == "__main__":
    db = get_database()
    if db is not None:
        print("✅ MongoDB connected")
        print(f"Collections: {db.list_collection_names()}")
    else:
        print("❌ MongoDB not connected")

    if get_blob_client():
        print("✅ Blob storage connected")
    else:
        print("❌ Blob storage not connected")