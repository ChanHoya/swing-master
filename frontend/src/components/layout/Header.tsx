"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import AuthModal from "@/components/auth/AuthModal";

export default function Header() {
  const { user, logout } = useAuth();
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-gray-950/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group" id="header-logo">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-indigo-500/30 group-hover:shadow-indigo-500/60 transition-shadow">
              S
            </div>
            <span className="font-bold text-lg tracking-tight">
              <span className="text-white">Swing</span>
              <span className="gradient-text">Master</span>
            </span>
          </Link>

          {/* Nav */}
          <nav className="flex items-center gap-4" id="header-nav">
            <Link href="/history" id="nav-history"
              className="text-sm text-slate-400 hover:text-white transition-colors">
              분석 기록
            </Link>
            <Link href="/guide" id="nav-guide"
              className="text-sm text-slate-400 hover:text-white transition-colors">
              스윙 7단계
            </Link>

            {user ? (
              /* 로그인 상태 */
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 hidden sm:block max-w-[120px] truncate">
                  {user.email}
                </span>
                <button onClick={logout}
                  className="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500">
                  로그아웃
                </button>
                <Link href="/upload" id="nav-cta"
                  className="btn-glow px-4 py-2 rounded-lg text-sm font-semibold text-white">
                  스윙 분석 시작
                </Link>
              </div>
            ) : (
              /* 비로그인 상태 */
              <div className="flex items-center gap-3">
                <button onClick={() => setShowModal(true)}
                  className="text-sm text-slate-300 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500">
                  로그인
                </button>
                <Link href="/upload" id="nav-cta"
                  className="btn-glow px-4 py-2 rounded-lg text-sm font-semibold text-white">
                  스윙 분석 시작
                </Link>
              </div>
            )}
          </nav>
        </div>
      </header>

      {showModal && <AuthModal onClose={() => setShowModal(false)} />}
    </>
  );
}
