"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useState } from "react";
import AuthModal from "@/components/auth/AuthModal";

const NAV_ITEMS = [
  { label: "분석", section: true },
  { href: "/",        icon: "📊", label: "대시보드" },
  { href: "/upload",  icon: "📤", label: "영상 업로드" },
  { href: "/guide",   icon: "🏌️", label: "7단계 가이드" },
  { label: "기록", section: true },
  { href: "/history", icon: "📋", label: "분석 기록" },
  { label: "기능 확장", section: true },
  { href: "/compare",  icon: "🔄", label: "비교 모드", soon: true },
  { href: "/coach",    icon: "💬", label: "AI 코치", soon: true },
  { href: "/progress", icon: "📈", label: "진행률", soon: true },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showAuth, setShowAuth] = useState(false);

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? "open" : ""}`}
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? "open" : ""}`}>
        {/* Brand */}
        <Link href="/" className="brand" onClick={onClose}>
          <div className="brand-mark">S</div>
          <div className="brand-name">
            Swing<span className="em">Master</span>
          </div>
        </Link>

        {/* Navigation */}
        {NAV_ITEMS.map((item, i) => {
          if (item.section) {
            return (
              <div key={i} className="nav-label">
                {item.label}
              </div>
            );
          }
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname?.startsWith(item.href!);
          return (
            <Link
              key={item.href}
              href={item.href!}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={onClose}
            >
              <span style={{ fontSize: 16, width: 20, textAlign: "center" }}>
                {item.icon}
              </span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.soon && (
                <span className="chip mono" style={{ fontSize: 8, padding: "2px 6px" }}>
                  SOON
                </span>
              )}
            </Link>
          );
        })}

        {/* Spacer */}
        <div className="nav-spacer" />

        {/* Weekly Goal */}
        <div className="goal-card">
          <div className="goal-label">이번 주 목표</div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            3:1 템포 잡기
          </div>
          <div className="goal-bar">
            <div className="goal-bar-fill" style={{ width: "60%" }} />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 6,
            }}
          >
            <span className="mono" style={{ fontSize: 10, color: "var(--text-2)" }}>
              3 / 5회
            </span>
            <span className="mono" style={{ fontSize: 10, color: "var(--accent)" }}>
              60%
            </span>
          </div>
        </div>

        {/* User Area */}
        <div style={{ borderTop: "1px solid var(--line)", paddingTop: 12, marginTop: 12 }}>
          {user ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 12px" }}>
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "var(--accent)",
                    color: "#0a0c10",
                    display: "grid",
                    placeItems: "center",
                    fontWeight: 800,
                    fontSize: 12,
                  }}
                >
                  {user.email[0].toUpperCase()}
                </div>
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--text-2)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                  }}
                >
                  {user.email}
                </span>
              </div>
              <button
                onClick={logout}
                className="btn sm"
                style={{ margin: "0 12px" }}
              >
                로그아웃
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuth(true)}
              className="btn"
              style={{ margin: "0 12px", width: "calc(100% - 24px)" }}
            >
              로그인 / 회원가입
            </button>
          )}
        </div>
      </aside>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </>
  );
}
