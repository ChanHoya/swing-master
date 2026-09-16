"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { apiClient } from "@/lib/api";

interface User {
  user_id: string;
  email: string;
  access_token: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("swingmaster_user");
    if (stored) setUser(JSON.parse(stored));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiClient.post("/auth/login", { email, password });
    const u: User = res.data;
    setUser(u);
    localStorage.setItem("swingmaster_user", JSON.stringify(u));
    // 이후 요청에 토큰 자동 첨부
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${u.access_token}`;
  };

  const register = async (email: string, password: string) => {
    const res = await apiClient.post("/auth/register", { email, password });
    const u: User = res.data;
    setUser(u);
    localStorage.setItem("swingmaster_user", JSON.stringify(u));
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${u.access_token}`;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("swingmaster_user");
    delete apiClient.defaults.headers.common["Authorization"];
  };

  // 앱 시작 시 토큰 재주입
  useEffect(() => {
    const stored = localStorage.getItem("swingmaster_user");
    if (stored) {
      const u = JSON.parse(stored) as User;
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${u.access_token}`;
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
