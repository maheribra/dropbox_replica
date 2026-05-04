

//  Firebase project configuration
const firebaseConfig = {
  apiKey: "AIzaSyAa-0BlEU6N_y5-0IVV3uqPPZQayYZzBIg",
  authDomain: "dropboxreplica-bba77.firebaseapp.com",
  projectId: "dropboxreplica-bba77",
  storageBucket: "dropboxreplica-bba77.firebasestorage.app",
  messagingSenderId: "790822196819",
  appId: "1:790822196819:web:85c494695c8f0c20c8d8a6",
  measurementId: "G-LGEZTHVCNM"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

async function signInWithGoogle() {
    try {
        const provider = new firebase.auth.GoogleAuthProvider();
        const result = await auth.signInWithPopup(provider);
        await verifyUserWithBackend(result.user);
    } catch (error) {
        console.error('Sign-In Error:', error);
        const errEl = document.getElementById('login-error');
        if (errEl) errEl.textContent = "Login failed: " + error.message;
    }
}

async function verifyUserWithBackend(user) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                displayName: user.displayName
            })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Save session info
            sessionStorage.setItem('user_id', data.user_id);
            sessionStorage.setItem('email', data.email);
            sessionStorage.setItem('root_directory_id', data.root_directory_id);

            console.log('User logged in:', data.email);
            toggleUI(true);
            initializeApp(); 
        } else {
            console.error('Backend rejected login');
        }
    } catch (error) {
        console.error('Network error during backend verification:', error);
    }
}

function toggleUI(isLoggedIn) {
    const loginScreen = document.getElementById('login-screen');
    const appScreen = document.getElementById('app-screen');

    if (isLoggedIn) {
        loginScreen.classList.remove('active');
        appScreen.classList.add('active');
    } else {
        loginScreen.classList.add('active');
        appScreen.classList.remove('active');
    }
}

async function logout() {
    await auth.signOut();
    sessionStorage.clear();
    toggleUI(false);
}

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('google-signin');
    if (loginBtn) loginBtn.onclick = signInWithGoogle;

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.onclick = logout;
});

async function logout() {
    await auth.signOut();
    sessionStorage.clear();
    toggleUI(false);
}

auth.onAuthStateChanged((user) => {
    if (user) {
        if (!sessionStorage.getItem('user_id')) {
            verifyUserWithBackend(user);
        } else {
            toggleUI(true);
        }
    } else {
        toggleUI(false);
    }
});