# ☁️ AdensDrive (Dropbox Replica)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0+-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg)](https://www.mongodb.com/atlas)
[![Storage](https://img.shields.io/badge/Azure-Blob_Storage-0078D4.svg)](https://azure.microsoft.com/en-us/services/storage/blobs/)

A high-performance, simplified replica of Dropbox built with **FastAPI**, **MongoDB Atlas**, **Firebase Auth**, and **Azure Blob Storage**.

---

## 🏗️ System Architecture
AdensDrive connects multiple cloud services into a unified file management experience:
*   **Identity Provider**: Firebase Auth (Google Sign-In) for secure, managed sessions.
*   **API Layer**: FastAPI handling asynchronous logic and routing.
*   **Metadata Store**: MongoDB Atlas tracking directory trees, file hashes, and sharing permissions.
*   **Object Storage**: Azure Blob Storage (or Azurite for local dev) hosting the actual file binaries.

---

## ✨ Features
*   **🔒 Secure Auth**: Firebase-based Google Sign-In with automated root directory provisioning.
*   **📂 Directory Logic**: Seamlessly create, delete, and navigate recursive directory structures.
*   **📤 File Operations**: Modern drag-and-drop uploads, downloads, and deletions.
*   **👯 Smart Duplicates**: SHA256 hashing to find identical files across specific folders or your entire storage.
*   **🔗 Read-Only Sharing**: Securely share files with other users via email without granting write access.
*   **🛠️ Developer Ready**: Pre-configured for local development using the Azurite emulator.

---

## 🚀 Quick Start

### 1. Clone & Environment
```bash
git clone <repository-url>
cd dropbox_clone
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration (.env)
Create a .env file in the root. You will need:

*   **MONGODB_URL**: Connection string from your MongoDB Atlas cluster.

*   **FIREBASE_CONFIG**: API Key and Project ID from your Firebase Console.

*   **AZURE_STORAGE_CONNECTION_STRING**: Default Azurite string for local or Azure Portal string for production.

### 3. Start Services
In one terminal, start the storage emulator:

```Bash
azurite --silent --location ./data
```

In another terminal, launch the application:

```Bash
python main.py
```

Visit: http://localhost:8000

## 📂 Project Structure

dropbox_replica/
├── routes/              # Modular API endpoints (Auth, Files, Directories)
├── static/              # Frontend assets
│   ├── js/              # app.js & firebase-login.js
│   └── css/             # style.css (Modernized UI)
├── main.py              # Application entry point
├── config.py            # Service initializations
├── models.py            # Pydantic data schemas
└── requirements.txt     # Dependency list

## 🛠️ Technical Details
### Duplicate Detection
The system uses a content-addressable approach. When a file is uploaded, a SHA256 hash is generated from the file stream.

*   **Storage**: The hash is saved in the MongoDB file document.

*   **Lookup**: Duplicate queries filter the collection by file_hash to identify identical content regardless of the filename.

### Database Schema Highlights
*   **Users**: Linked via Firebase uid to ensure secure identity mapping.

*   **Directories**: Uses a self-referencing tree model with parent_id.

*   **Files**: Metadata is stored in MongoDB; the actual binary is retrieved via a blob_url from Azure.

*   **Shares**: A mapping collection that defines permissions between file_id and shared_with_id.

## 🛡️ Security Notes
*   **Cross-User Isolation**: Every database query is scoped by the user_id derived from the validated Firebase token.

*   **Path Traversal Protection**: Directory navigation is strictly validated against the user's root ownership.

*   **Secret Management**: Sensitive keys are loaded via python-dotenv and should never be committed to source control.

## 📜 License
This project is for educational purposes. All rights to the "Dropbox" brand belong to Dropbox, Inc.
