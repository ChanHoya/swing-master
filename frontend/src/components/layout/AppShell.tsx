"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-content">
        {/* Mobile menu button */}
        <button
          className="mobile-menu-btn items-center gap-2"
          onClick={() => setSidebarOpen(true)}
          aria-label="메뉴 열기"
          style={{ marginBottom: 16 }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
          <span style={{ fontSize: 12, fontWeight: 600 }}>메뉴</span>
        </button>
        {children}
      </div>
    </div>
  );
}
