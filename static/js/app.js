
// Application State
let appState = {
    currentDirectoryId: null,
    currentDirectoryPath: '/',
    userId: null,
    rootDirectoryId: null,
    userEmail: null
};

// Modal callbacks for deferred actions
let confirmCallback = null;
let inputCallback = null;

async function initializeApp() {
    appState.userId = sessionStorage.getItem('user_id');
    appState.rootDirectoryId = sessionStorage.getItem('root_directory_id');
    appState.userEmail = sessionStorage.getItem('email');
    
    if (appState.userId && appState.rootDirectoryId) {
        // Update UI with user info
        document.getElementById('user-email').textContent = appState.userEmail;
        
        // Navigate to root directory
        appState.currentDirectoryId = appState.rootDirectoryId;
        await loadDirectoryContents();
    }
}

function setupEventListeners() {
    // Navigation buttons
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('back-btn').addEventListener('click', goBackDirectory);
    
    // File operations
    document.getElementById('upload-file-btn').addEventListener('click', openUploadModal);
    document.getElementById('new-folder-btn').addEventListener('click', createNewFolder);
    
    // Tools
    document.getElementById('duplicates-dir-btn').addEventListener('click', showDuplicatesInDirectory);
    document.getElementById('duplicates-all-btn').addEventListener('click', showDuplicatesAll);
    document.getElementById('shared-with-me-btn').addEventListener('click', showSharedWithMe);
    document.getElementById('my-shares-btn').addEventListener('click', showMyShares);
    
    // Modal handlers
    setupModalHandlers();
    
    // Upload drag and drop
    setupUploadHandlers();
}


function setupModalHandlers() {
    // Confirmation modal
    const confirmYes = document.getElementById('confirm-yes');
    if (confirmYes) confirmYes.addEventListener('click', () => {
        hideModal('confirm-modal');
        if (confirmCallback) confirmCallback(true);
    });
    
    const confirmNo = document.getElementById('confirm-no');
    if (confirmNo) confirmNo.addEventListener('click', () => {
        hideModal('confirm-modal');
        if (confirmCallback) confirmCallback(false);
    });
    
    // Input modal
    const inputSubmit = document.getElementById('input-submit');
    if (inputSubmit) inputSubmit.addEventListener('click', () => {
        const value = document.getElementById('input-field').value;
        hideModal('input-modal');
        if (inputCallback) inputCallback(value);
    });
    
    const inputCancel = document.getElementById('input-cancel');
    if (inputCancel) inputCancel.addEventListener('click', () => {
        hideModal('input-modal');
        if (inputCallback) inputCallback(null);
    });
    
    // Duplicates modal
    const duplicatesClose = document.getElementById('duplicates-close');
    if (duplicatesClose) duplicatesClose.addEventListener('click', () => {
        hideModal('duplicates-modal');
    });
    
    const duplicatesModalClose = document.getElementById('duplicates-modal-close');
    if (duplicatesModalClose) duplicatesModalClose.addEventListener('click', () => {
        hideModal('duplicates-modal');
    });
    
    // Upload modal cancel button
    const uploadCancelBtn = document.getElementById('upload-cancel');
    if (uploadCancelBtn) {
        uploadCancelBtn.addEventListener('click', () => {
            hideModal('upload-modal');
            const fileInput = document.getElementById('file-input');
            if (fileInput) fileInput.value = '';
        });
    }
}


function setupUploadHandlers() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (!uploadArea || !fileInput) {
        console.error('Upload area or file input not found');
        return;
    }
    
    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Drag over
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    // Drag leave
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    // Drop
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            uploadFile();
        }
    });
    
    // File selected
    fileInput.addEventListener('change', uploadFile);
}


async function loadDirectoryContents() {
    try {
        const response = await fetch(
            `/api/directories/contents?directory_id=${appState.currentDirectoryId}&user_id=${appState.userId}`
        );
        
        if (!response.ok) {
            showError('Failed to load directory');
            return;
        }
        
        const data = await response.json();
        appState.currentDirectoryPath = data.current_directory.path;
        
        // Update breadcrumb
        updateBreadcrumb(data.current_directory.path);
        
        // Update back button visibility
        const backBtn = document.getElementById('back-btn');
        backBtn.style.display = data.parent_available ? 'block' : 'none';
        
        // Render file list
        renderFileList(data);
    } catch (error) {
        showError('Error loading directory: ' + error.message);
    }
}


function updateBreadcrumb(path) {
    document.getElementById('breadcrumb-path').textContent = path === '/' ? '/' : path;
}


function renderFileList(data) {
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';
    
    // Add parent directory navigation if not in root
    if (!data.current_directory.is_root) {
        const parentItem = document.createElement('div');
        parentItem.className = 'file-item parent-item';
        parentItem.innerHTML = `
            <div class="col-name"><span class="icon">📁</span> ..</div>
            <div class="col-type">Parent</div>
            <div class="col-size">-</div>
            <div class="col-date">-</div>
            <div class="col-actions"></div>
        `;
        parentItem.addEventListener('click', goBackDirectory);
        fileList.appendChild(parentItem);
    }
    
    // Add directories
    data.subdirectories.forEach(dir => {
        const item = createFileItemElement(dir, true);
        fileList.appendChild(item);
    });
    
    // Add files
    data.files.forEach(file => {
        const item = createFileItemElement(file, false);
        fileList.appendChild(item);
    });
    
    if (data.subdirectories.length === 0 && data.files.length === 0 && data.current_directory.is_root) {
        fileList.innerHTML = '<div class="empty-message">Your Dropbox is empty. Start by uploading a file or creating a folder!</div>';
    }
}


function createFileItemElement(item, isDirectory) {
    const itemEl = document.createElement('div');
    itemEl.className = 'file-item';
    itemEl.dataset.itemId = item.id;
    itemEl.dataset.itemName = item.name;
    
    const icon = isDirectory ? '📂' : '📄';
    const type = isDirectory ? 'Folder' : 'File';
    const size = isDirectory ? '-' : formatFileSize(item.size);
    const date = isDirectory ? '-' : formatDate(item.created_at);
    
    let actionsHTML = '';
    if (isDirectory) {
        actionsHTML = `
            <button class="action-btn" data-action="enter">📂 Open</button>
            <button class="action-btn" data-action="delete">🗑️ Delete</button>
        `;
    } else {
        actionsHTML = `
            <button class="action-btn" data-action="download">⬇️ Download</button>
            <button class="action-btn" data-action="share">📤 Share</button>
            <button class="action-btn" data-action="delete">🗑️ Delete</button>
        `;
    }
    
    itemEl.innerHTML = `
        <div class="col-name"><span class="icon">${icon}</span> ${item.name}</div>
        <div class="col-type">${type}</div>
        <div class="col-size">${size}</div>
        <div class="col-date">${date}</div>
        <div class="col-actions">${actionsHTML}</div>
    `;
    
    // Add event listeners to action buttons
    itemEl.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            
            if (action === 'enter' && isDirectory) {
                await enterDirectory(item.id);
            } else if (action === 'download' && !isDirectory) {
                downloadFile(item.id, item.name);
            } else if (action === 'share' && !isDirectory) {
                openShareModal(item.id, item.name);
            } else if (action === 'delete') {
                if (isDirectory) {
                    deleteDirectory(item.id, item.name);
                } else {
                    deleteFile(item.id, item.name);
                }
            }
        });
    });
    
    return itemEl;
}


async function enterDirectory(directoryId) {
    appState.currentDirectoryId = directoryId;
    await loadDirectoryContents();
}

async function goBackDirectory() {
    try {
        const response = await fetch('/api/directories/navigate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_directory_id: appState.currentDirectoryId,
                direction: 'up',
                user_id: appState.userId
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            appState.currentDirectoryId = data.new_directory_id;
            await loadDirectoryContents();
        }
    } catch (error) {
        showError('Error navigating: ' + error.message);
    }
}

function createNewFolder() {
    showInputModal('New Folder', 'Enter folder name:', (name) => {
        if (name) {
            createFolderAPI(name);
        }
    });
}

async function createFolderAPI(dirName) {
    try {
        const response = await fetch('/api/directories/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                parent_directory_id: appState.currentDirectoryId,
                directory_name: dirName,
                user_id: appState.userId
            })
        });
        
        if (response.ok) {
            showSuccess('Folder created successfully');
            await loadDirectoryContents();  // ✅ THIS IS CRITICAL
        } else {
            const error = await response.json();
            showError(error.detail);
        }
    } catch (error) {
        showError('Error creating folder: ' + error.message);
    }
}

function deleteDirectory(directoryId, dirName) {
    showConfirmation(
        `Delete folder "${dirName}"?`,
        'This folder will be permanently deleted.',
        async (confirmed) => {
            if (confirmed) {
                try {
                    const response = await fetch('/api/directories/delete', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            directory_id: directoryId,
                            user_id: appState.userId
                        })
                    });
                    
                    if (response.ok) {
                        showSuccess('Folder deleted successfully');
                        await loadDirectoryContents();
                    } else {
                        const error = await response.json();
                        showError(error.detail);
                    }
                } catch (error) {
                    showError('Error deleting folder: ' + error.message);
                }
            }
        }
    );
}


function openUploadModal() {
    showModal('upload-modal');
}

async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput.files.length) return;
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('directory_id', appState.currentDirectoryId);
    formData.append('user_id', appState.userId);
    
    try {
        showUploadProgress(true);
        
        const response = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        console.log('Upload response:', data);
        
        if (data.status === 'exists') {
            // File exists, ask for confirmation
            showUploadProgress(false);
            hideModal('upload-modal');
            
            showConfirmation(
                `File "${data.file_name}" already exists`,
                'Do you want to overwrite it?',
                async (confirmed) => {
                    if (confirmed) {
                        await overwriteFile(data.file_id, file);
                    } else {
                        // User clicked No - just refresh and show the original file
                         fileInput.value = '';
                         await loadDirectoryContents();
                    }
                }
            );
        } else if (data.status === 'success') {
            showUploadProgress(false);
            hideModal('upload-modal');
            showSuccess('File uploaded successfully');
            fileInput.value = '';
            console.log('Calling loadDirectoryContents...');
            await loadDirectoryContents();
        } else {
            showUploadProgress(false);
            showError('Unknown upload response');
        }
    } catch (error) {
        showUploadProgress(false);
        showError('Upload error: ' + error.message);
    }
}

async function overwriteFile(fileId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('directory_id', appState.currentDirectoryId);
    formData.append('user_id', appState.userId);
    formData.append('file_id', fileId);
    
    try {
        showUploadProgress(true);
        
        const response = await fetch('/api/files/upload/overwrite', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showUploadProgress(false);
            showSuccess('File overwritten successfully');
            await loadDirectoryContents();
        }
    } catch (error) {
        showUploadProgress(false);
        showError('Overwrite error: ' + error.message);
    }
}

function deleteFile(fileId, fileName) {
    showConfirmation(
        `Delete file "${fileName}"?`,
        'This action cannot be undone.',
        async (confirmed) => {
            if (confirmed) {
                try {
                    const response = await fetch(
                        `/api/files/delete?file_id=${fileId}&user_id=${appState.userId}`,
                        { method: 'DELETE' }
                    );
                    
                    if (response.ok) {
                        showSuccess('File deleted successfully');
                        await loadDirectoryContents();
                    }
                } catch (error) {
                    showError('Error deleting file: ' + error.message);
                }
            }
        }
    );
}


function downloadFile(fileId, fileName) {
    const url = `/api/files/download?file_id=${fileId}&user_id=${appState.userId}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function openShareModal(fileId, fileName) {
    const modal = document.getElementById('share-modal');
    modal.dataset.fileId = fileId;
    
    document.getElementById('share-submit').onclick = async () => {
        const email = document.getElementById('share-email').value;
        if (email) {
            await shareFile(fileId, email);
            hideModal('share-modal');
            document.getElementById('share-email').value = '';
        }
    };
    
    document.getElementById('share-cancel').onclick = () => {
        hideModal('share-modal');
    };
    
    showModal('share-modal');
}

async function shareFile(fileId, email) {
    try {
        const response = await fetch('/api/sharing/share', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: fileId,
                owner_id: appState.userId,
                shared_with_email: email
            })
        });
        
        if (response.ok) {
            showSuccess(`File shared with ${email}`);
        } else {
            const error = await response.json();
            showError(error.detail);
        }
    } catch (error) {
        showError('Error sharing file: ' + error.message);
    }
}

async function showSharedWithMe() {
    try {
        const response = await fetch(`/api/sharing/shared-with-me?user_id=${appState.userId}`);
        
        if (!response.ok) {
            showError('Failed to load shared files');
            return;
        }
        
        const data = await response.json();
        
        const modal = document.getElementById('duplicates-modal');
        document.getElementById('duplicates-title').textContent = 'Files Shared With Me';
        
        let html = '<div class="shared-files-list">';
        if (!data.shared_files || data.shared_files.length === 0) {
            html += '<p>No files shared with you yet.</p>';
        } else {
            data.shared_files.forEach(file => {
                html += `
                    <div class="shared-file-item">
                        <div>
                            <strong>${file.file_name}</strong><br>
                            From: ${file.owner_email}<br>
                            Shared: ${formatDate(file.shared_at)}
                        </div>
                        <button onclick="downloadFile('${file.file_id}', '${file.file_name}')" class="action-btn">
                            ⬇️ Download
                        </button>
                    </div>
                `;
            });
        }
        html += '</div>';
        
        document.getElementById('duplicates-list').innerHTML = html;
        showModal('duplicates-modal');
    } catch (error) {
        showError('Error loading shared files: ' + error.message);
    }
}

async function showMyShares() {
    try {
        const response = await fetch(`/api/sharing/my-shares?user_id=${appState.userId}`);
        
        if (!response.ok) {
            showError('Failed to load shares');
            return;
        }
        
        const data = await response.json();
        
        const modal = document.getElementById('duplicates-modal');
        document.getElementById('duplicates-title').textContent = 'Files I\'m Sharing';
        
        let html = '<div class="shared-files-list">';
        if (!data.my_shares || data.my_shares.length === 0) {
            html += '<p>You haven\'t shared any files yet.</p>';
        } else {
            data.my_shares.forEach(share => {
                html += `
                    <div class="shared-file-item">
                        <div>
                            <strong>${share.file_name}</strong><br>
                            Shared with: ${share.shared_with_email}<br>
                            Shared on: ${formatDate(share.shared_at)}
                        </div>
                    </div>
                `;
            });
        }
        html += '</div>';
        
        document.getElementById('duplicates-list').innerHTML = html;
        showModal('duplicates-modal');
    } catch (error) {
        showError('Error loading shares: ' + error.message);
    }
}

async function showDuplicatesInDirectory() {
    try {
        const response = await fetch(
            `/api/files/duplicates/directory?directory_id=${appState.currentDirectoryId}&user_id=${appState.userId}`
        );
        
        if (!response.ok) {
            showError('Failed to load duplicates');
            return;
        }
        
        const data = await response.json();
        
        document.getElementById('duplicates-title').textContent = 'Duplicate Files (Current Directory)';
        
        if (data.duplicates && data.duplicates.length > 0) {
            renderDuplicatesView(data.duplicates);
        } else {
            document.getElementById('duplicates-list').innerHTML = '<p>No duplicate files found.</p>';
        }
        
        showModal('duplicates-modal');
    } catch (error) {
        showError('Error finding duplicates: ' + error.message);
    }
}

async function showDuplicatesAll() {
    try {
        const response = await fetch(`/api/files/duplicates/all?user_id=${appState.userId}`);
        
        if (!response.ok) {
            showError('Failed to load duplicates');
            return;
        }
        
        const data = await response.json();
        
        const duplicateCount = data.total_duplicate_count || 0;
        document.getElementById('duplicates-title').textContent = `Duplicate Files (All Locations) - ${duplicateCount} duplicates`;
        
        if (data.duplicates && data.duplicates.length > 0) {
            renderDuplicatesView(data.duplicates);
        } else {
            document.getElementById('duplicates-list').innerHTML = '<p>No duplicate files found.</p>';
        }
        
        showModal('duplicates-modal');
    } catch (error) {
        showError('Error finding duplicates: ' + error.message);
    }
}

function renderDuplicatesView(duplicates) {
    let html = '';
    
    if (duplicates.length === 0) {
        html = '<p>No duplicate files found.</p>';
    } else {
        duplicates.forEach((group, index) => {
            html += `
                <div class="duplicate-group">
                    <h4>Duplicate Group ${index + 1} (Hash: ${group.hash.substring(0, 8)}...)</h4>
                    <div class="duplicate-files">
            `;
            
            group.files.forEach(file => {
                html += `
                    <div class="duplicate-file" style="background: #fffacd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                        <strong>📄 ${file.name}</strong><br>
                        Size: ${formatFileSize(file.size)}<br>
                        ${file.path ? `Path: ${file.path}<br>` : ''}
                    </div>
                `;
            });
            
            html += '</div></div>';
        });
    }
    
    document.getElementById('duplicates-list').innerHTML = html;
}

function showConfirmation(title, message, callback) {
    confirmCallback = callback;
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    showModal('confirm-modal');
}

function showInputModal(title, placeholder, callback) {
    inputCallback = callback;
    document.getElementById('input-title').textContent = title;
    document.getElementById('input-field').placeholder = placeholder;
    document.getElementById('input-field').value = '';
    showModal('input-modal');
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

function showUploadProgress(show) {
    const progress = document.getElementById('upload-progress');
    if (progress) {
        progress.classList.toggle('hidden', !show);
    }
}

function showSuccess(message) {
    showStatusMessage(message, 'success');
}

function showError(message) {
    showStatusMessage(message, 'error');
}

function showStatusMessage(message, type) {
    const statusArea = document.getElementById('status-area');
    const msgEl = document.createElement('div');
    msgEl.className = `status-message status-${type}`;
    msgEl.textContent = message;
    
    statusArea.innerHTML = '';
    statusArea.appendChild(msgEl);
    
    setTimeout(() => {
        msgEl.remove();
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    
    // Check if user is logged in and initialize app
    const userId = sessionStorage.getItem('user_id');
    if (userId) {
        initializeApp();
    }
});

// Expose functions globally so they can be called from HTML onclick
window.initializeApp = initializeApp;
window.logout = logout;