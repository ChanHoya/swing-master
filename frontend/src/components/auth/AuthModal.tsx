"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

interface Props {
  onClose: () => void;
}

export default function AuthModal({ onClose }: Props) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? "오류가 발생했습니다. 다시 시도해주세요.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 50,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 16,
        background: "rgba(0,0,0,0.7)",
        backdropFilter: "blur(6px)",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%", maxWidth: 380,
          borderRadius: 16, padding: 32,
          position: "relative",
          background: "var(--bg)",
          border: "1px solid var(--line-2)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 16, right: 16,
            background: "none", border: "none",
            color: "var(--text-3)", fontSize: 20,
            cursor: "pointer",
          }}
        >
          ×
        </button>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div className="flex items-center justify-center gap-2 mb-1">
            <div className="brand-mark" style={{ width: 28, height: 28, fontSize: 14 }}>S</div>
            <span style={{ fontWeight: 800, fontSize: 16 }}>
              Swing<span className="em">Master</span>
            </span>
          </div>
          <p className="text-muted text-small">
            {mode === "login" ? "계정에 로그인하세요" : "새 계정을 만드세요"}
          </p>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            borderRadius: 10,
            overflow: "hidden",
            marginBottom: 24,
            background: "var(--bg-3)",
            border: "1px solid var(--line)",
          }}
        >
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(""); }}
              style={{
                flex: 1,
                padding: "10px 0",
                fontSize: 13,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                transition: "all 0.15s",
                background: mode === m ? "var(--accent)" : "transparent",
                color: mode === m ? "#0a0c10" : "var(--text-3)",
              }}
            >
              {m === "login" ? "로그인" : "회원가입"}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ display: "block", fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                fontSize: 13,
                color: "var(--text)",
                outline: "none",
                background: "var(--bg-3)",
                border: "1px solid var(--line)",
                transition: "border-color 0.15s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--line)")}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder={mode === "register" ? "6자 이상" : "••••••••"}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                fontSize: 13,
                color: "var(--text)",
                outline: "none",
                background: "var(--bg-3)",
                border: "1px solid var(--line)",
                transition: "border-color 0.15s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--line)")}
            />
          </div>

          {error && (
            <div className="msg bad" style={{ fontSize: 12 }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn primary lg w-full"
            style={{
              justifyContent: "center",
              opacity: loading ? 0.6 : 1,
              marginTop: 4,
            }}
          >
            {loading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}
          </button>
        </form>
      </div>
    </div>
  );
}
