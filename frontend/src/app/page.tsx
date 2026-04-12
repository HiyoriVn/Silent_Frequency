"use client";

import React from "react";
import PuzzleScreen from "@/components/PuzzleScreen";
import { createSession, loginUser, logoutUser, registerUser } from "@/lib/api";
import type { SelfAssessedLevel } from "@/lib/types";

const AUTH_STORAGE_KEY = "sf_auth_v1";

type AuthSession = {
  userId: string;
  username: string;
  realName: string | null;
  authToken: string;
};

type AuthFormProps = {
  authMode: "register" | "login";
  setAuthMode: React.Dispatch<React.SetStateAction<"register" | "login">>;
  username: string;
  setUsername: React.Dispatch<React.SetStateAction<string>>;
  password: string;
  setPassword: React.Dispatch<React.SetStateAction<string>>;
  realName: string;
  setRealName: React.Dispatch<React.SetStateAction<string>>;
  authLoading: boolean;
  authError: string | null;
  submitAuth: (event: React.FormEvent) => Promise<void>;
};

type SessionStartPanelProps = {
  username: string;
  displayName: string;
  setDisplayName: React.Dispatch<React.SetStateAction<string>>;
  selfAssessedLevel: SelfAssessedLevel | null;
  setSelfAssessedLevel: React.Dispatch<
    React.SetStateAction<SelfAssessedLevel | null>
  >;
  loading: boolean;
  error: string | null;
  handleLogout: () => Promise<void>;
  startGameplayV2: (event: React.FormEvent) => Promise<void>;
};

const SELF_ASSESSED_LEVELS: SelfAssessedLevel[] = [
  "beginner",
  "elementary",
  "intermediate",
  "upper_intermediate",
];

function readStoredAuth(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (
      !parsed ||
      typeof parsed.userId !== "string" ||
      typeof parsed.username !== "string" ||
      typeof parsed.authToken !== "string"
    ) {
      return null;
    }
    return {
      userId: parsed.userId,
      username: parsed.username,
      realName: parsed.realName ?? null,
      authToken: parsed.authToken,
    };
  } catch {
    return null;
  }
}

function persistAuth(auth: AuthSession | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (!auth) {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

function AuthForm({
  authMode,
  setAuthMode,
  username,
  setUsername,
  password,
  setPassword,
  realName,
  setRealName,
  authLoading,
  authError,
  submitAuth,
}: AuthFormProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center gap-6 px-4">
      <h1 className="text-4xl font-semibold tracking-wide text-neutral-100">
        Silent Frequency
      </h1>
      <p className="text-sm text-neutral-500">Batch 1.1 minimal auth</p>

      <div className="inline-flex rounded-md border border-neutral-700 p-1">
        <button
          type="button"
          onClick={() => setAuthMode("login")}
          className={`rounded px-3 py-1 text-sm ${authMode === "login" ? "bg-neutral-700 text-white" : "text-neutral-300"}`}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setAuthMode("register")}
          className={`rounded px-3 py-1 text-sm ${authMode === "register" ? "bg-neutral-700 text-white" : "text-neutral-300"}`}
        >
          Register
        </button>
      </div>

      <form onSubmit={submitAuth} className="w-full space-y-3">
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="Username"
          className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-neutral-100"
        />
        {authMode === "register" && (
          <input
            value={realName}
            onChange={(event) => setRealName(event.target.value)}
            placeholder="Real name (optional)"
            className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-neutral-100"
          />
        )}
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder={
            authMode === "register" ? "Password (min 8 chars)" : "Password"
          }
          className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-neutral-100"
        />
        <button
          type="submit"
          disabled={authLoading || !username.trim() || !password}
          className="w-full rounded-md bg-cyan-600 px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          {authLoading
            ? "Working..."
            : authMode === "register"
              ? "Create account"
              : "Login"}
        </button>
      </form>

      {authError && <p className="text-sm text-red-400">{authError}</p>}
    </main>
  );
}

function SessionStartPanel({
  username,
  displayName,
  setDisplayName,
  selfAssessedLevel,
  setSelfAssessedLevel,
  loading,
  error,
  handleLogout,
  startGameplayV2,
}: SessionStartPanelProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center gap-6 px-4">
      <h1 className="text-4xl font-semibold tracking-wide text-neutral-100">
        Silent Frequency
      </h1>
      <p className="text-sm text-neutral-500">Authenticated as {username}</p>

      <button
        type="button"
        onClick={handleLogout}
        className="rounded-md border border-neutral-600 px-4 py-2 text-sm text-neutral-200"
      >
        Logout
      </button>

      <section className="w-full space-y-3 rounded-md border border-neutral-700 bg-neutral-900/60 p-4">
        <h2 className="text-lg font-medium text-neutral-100">
          Quick Self-Assessment
        </h2>
        <p className="text-sm text-neutral-400">
          Select your current English level to continue.
        </p>
        <div className="grid gap-2">
          {SELF_ASSESSED_LEVELS.map((level) => (
            <label
              key={level}
              className="flex cursor-pointer items-center gap-2 rounded border border-neutral-700 px-3 py-2 text-neutral-200"
            >
              <input
                type="radio"
                name="self_assessed_level"
                value={level}
                checked={selfAssessedLevel === level}
                onChange={() => setSelfAssessedLevel(level)}
              />
              <span>{level.replaceAll("_", " ")}</span>
            </label>
          ))}
        </div>
      </section>

      <form onSubmit={startGameplayV2} className="w-full space-y-3">
        <input
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="Enter display name"
          className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-neutral-100"
        />
        <button
          type="submit"
          disabled={loading || !displayName.trim() || !selfAssessedLevel}
          className="w-full rounded-md bg-cyan-600 px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          {loading ? "Starting..." : "Start gameplay_v2"}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}
    </main>
  );
}

export default function Home() {
  const [authMode, setAuthMode] = React.useState<"register" | "login">("login");
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [realName, setRealName] = React.useState("");
  const [isHydrated, setIsHydrated] = React.useState(false);
  const [auth, setAuth] = React.useState<AuthSession | null>(null);
  const [authLoading, setAuthLoading] = React.useState(false);
  const [authError, setAuthError] = React.useState<string | null>(null);
  const [selfAssessedLevel, setSelfAssessedLevel] =
    React.useState<SelfAssessedLevel | null>(null);
  const [displayName, setDisplayName] = React.useState<string>("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const stored = readStoredAuth();
    if (stored) {
      setAuth(stored);
      setDisplayName(stored.realName?.trim() || stored.username);
    }
    setIsHydrated(true);
  }, []);

  const submitAuth = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password) {
      setAuthError("Username and password are required");
      return;
    }
    if (authMode === "register" && password.length < 8) {
      setAuthError("Password must be at least 8 characters");
      return;
    }

    setAuthLoading(true);
    setAuthError(null);
    setError(null);

    const response =
      authMode === "register"
        ? await registerUser(
            username.trim(),
            password,
            realName.trim() || undefined,
          )
        : await loginUser(username.trim(), password);

    if (!response.ok || !response.data) {
      setAuthError(response.error?.message ?? "Authentication failed");
      setAuthLoading(false);
      return;
    }

    const nextAuth: AuthSession = {
      userId: response.data.user_id,
      username: response.data.username,
      realName: response.data.real_name,
      authToken: response.data.auth_token,
    };
    setAuth(nextAuth);
    persistAuth(nextAuth);
    setDisplayName(nextAuth.realName?.trim() || nextAuth.username);
    setSelfAssessedLevel(null);
    setPassword("");
    setRealName("");
    setAuthLoading(false);
  };

  const handleLogout = async () => {
    const currentAuth = auth;
    if (!currentAuth) {
      return;
    }

    setAuthLoading(true);
    await logoutUser(currentAuth.authToken);

    persistAuth(null);
    setAuth(null);
    setSessionId(null);
    setDisplayName("");
    setUsername("");
    setPassword("");
    setRealName("");
    setSelfAssessedLevel(null);
    setError(null);
    setAuthError(null);
    setAuthLoading(false);
  };

  const startGameplayV2 = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!auth || !displayName.trim() || !selfAssessedLevel) return;

    setLoading(true);
    setError(null);
    const response = await createSession(
      displayName.trim(),
      "adaptive",
      "gameplay_v2",
      selfAssessedLevel,
    );
    if (!response.ok || !response.data) {
      setError(
        response.error?.message ?? "Failed to create gameplay_v2 session",
      );
      setLoading(false);
      return;
    }

    setSessionId(response.data.session_id);
    setLoading(false);
  };

  if (!isHydrated) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center gap-4 px-4">
        <h1 className="text-4xl font-semibold tracking-wide text-neutral-100">
          Silent Frequency
        </h1>
        <p className="text-sm text-neutral-500">Loading...</p>
      </main>
    );
  }

  if (!auth) {
    return (
      <AuthForm
        authMode={authMode}
        setAuthMode={setAuthMode}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        realName={realName}
        setRealName={setRealName}
        authLoading={authLoading}
        authError={authError}
        submitAuth={submitAuth}
      />
    );
  }

  if (!sessionId) {
    return (
      <SessionStartPanel
        username={auth.username}
        displayName={displayName}
        setDisplayName={setDisplayName}
        selfAssessedLevel={selfAssessedLevel}
        setSelfAssessedLevel={setSelfAssessedLevel}
        loading={loading}
        error={error}
        handleLogout={handleLogout}
        startGameplayV2={startGameplayV2}
      />
    );
  }

  return (
    <main className="min-h-screen px-4 py-8">
      <PuzzleScreen sessionId={sessionId} />
    </main>
  );
}
