import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";

// Fill these in from Firebase console -> Project settings -> General -> Your apps
// (or set them as Vite env vars: VITE_FIREBASE_API_KEY, etc.)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const isFirebaseConfigured = Boolean(firebaseConfig.apiKey);

let app = null;
let auth = null;
let provider = null;

if (isFirebaseConfigured) {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
  provider = new GoogleAuthProvider();
}

export { auth };

export function loginWithGoogle() {
  if (!isFirebaseConfigured) {
    return Promise.reject(new Error("Firebase is not configured. Using demo-user mode."));
  }
  return signInWithPopup(auth, provider);
}

export function logout() {
  if (!isFirebaseConfigured) {
    return Promise.resolve();
  }
  return signOut(auth);
}

export function watchAuthState(callback) {
  if (!isFirebaseConfigured) {
    callback(null);
    return () => {};
  }
  return onAuthStateChanged(auth, callback);
}