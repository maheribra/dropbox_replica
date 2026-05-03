from pymongo import MongoClient
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "dropbox_replica")

try:
    mongo_client = MongoClient(MONGODB_URL)
    database = mongo_client[DATABASE_NAME]
except Exception as e:
    print("MongoDB connection failed:", e)
    database = None


# Azure / Azurite setup
AZURE_STORAGE_CONNECTION_STRING = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

BLOB_CONTAINER_NAME = "dropbox-files"

try:
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

    # Check if container exists; if not, create it
    if not container_client.exists():
        container_client.create_container()
        print(f"Container '{BLOB_CONTAINER_NAME}' created.")
    else:
        print(f"Container '{BLOB_CONTAINER_NAME}' already exists.")

except Exception as e:
    print("Azurite connection failed deeply:", e)
    blob_service_client = None


def get_database():
    return database


def get_blob_client():
    return blob_service_client

def get_database():
    return database

def get_blob_client():
    return blob_service_client

if __name__ == "__main__":
    db = get_database()
    if db is not None:
        print("MongoDB connected")
        print("Collections:", db.list_collection_names())
    else:
        print("MongoDB not connected")

    if get_blob_client():
        print("Blob storage connected")
    else:
        print("Blob storage not connected")