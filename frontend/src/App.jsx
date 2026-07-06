import React from "react";
import { watchAuthState } from "./firebase";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [user, setUser] = React.useState(undefined); // undefined = loading, null = signed out
  const [idToken, setIdToken] = React.useState(null);

  React.useEffect(() => {
    const unsubscribe = watchAuthState(async (u) => {
      setUser(u);
      if (u) {
        const token = u.getIdToken ? await u.getIdToken() : null;
        setIdToken(token);
      } else {
        setIdToken(null);
      }
    });
    return unsubscribe;
  }, []);

  function handleDemoLogin() {
    setUser({
      displayName: "Demo User",
      email: "demo@local",
      getIdToken: async () => null,
    });
    setIdToken(null);
  }

  if (user === undefined) {
    return (
      <div className="min-h-screen flex items-center justify-center text-mist">
        Loading TruthShield…
      </div>
    );
  }

  return user ? (
    <Dashboard user={user} idToken={idToken} />
  ) : (
    <Login onDemoLogin={handleDemoLogin} />
  );
}