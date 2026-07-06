import React from "react";
import { loginWithGoogle } from "../firebase";

export default function Login({ onDemoLogin }) {
  const [error, setError] = React.useState(null);

  async function handleLogin() {
    setError(null);
    try {
      await loginWithGoogle();
    } catch (e) {
      setError("Sign-in failed. Check your Firebase config in .env.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 justify-center mb-8">
          <ShieldMark />
          <span className="font-display text-2xl font-semibold tracking-tight text-white">
            TruthShield <span className="text-verify">AI</span>
          </span>
        </div>
        <div className="bg-panel border border-line rounded-2xl p-8 shadow-glow">
          <h1 className="font-display text-xl text-white mb-1">Verify before you trust</h1>
          <p className="text-mist text-sm mb-6">
            Sign in to run any AI answer through six independent checks —
            evidence, facts, sources, and safety — before it reaches you.
          </p>
          <button
            onClick={handleLogin}
            className="w-full flex items-center justify-center gap-3 bg-white text-ink font-medium rounded-xl py-3 hover:bg-mist/90 transition-colors"
          >
            <GoogleG />
            Continue with Google
          </button>
          <button
            onClick={onDemoLogin}
            className="w-full mt-3 flex items-center justify-center gap-2 bg-transparent border border-line text-mist font-medium rounded-xl py-3 hover:bg-white/5 transition-colors"
          >
            Continue as Demo User
          </button>
          {error && <p className="text-danger text-sm mt-4">{error}</p>}
          <p className="text-mist/60 text-xs mt-6 text-center">
            Authenticated with Firebase. Your reports stay tied to your account.
          </p>
        </div>
      </div>
    </div>
  );
}

function ShieldMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <path d="M16 2L28 7V15C28 22.5 22.8 27.8 16 30C9.2 27.8 4 22.5 4 15V7L16 2Z" fill="#16212C" stroke="#2DD4BF" strokeWidth="1.5" />
      <path d="M11 16L14.5 19.5L21 12" stroke="#2DD4BF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 01-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.96v2.33A9 9 0 009 18z" />
      <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 013.68 9c0-.59.1-1.17.27-1.7V4.97H.96A9 9 0 000 9c0 1.45.35 2.83.96 4.03l2.99-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 00.96 4.97l2.99 2.33C4.66 5.17 6.65 3.58 9 3.58z" />
    </svg>
  );
}