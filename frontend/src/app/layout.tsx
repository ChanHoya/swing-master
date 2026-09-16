import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Swing Master — AI 골프 스윙 분석",
  description:
    "스윙 영상을 업로드하면 AI가 자세를 분석하고 교정 피드백과 드릴을 제공합니다. 레슨 없이 전문가 수준의 골프 코칭을 경험하세요.",
  keywords: ["골프", "스윙 분석", "AI 코칭", "골프 레슨", "swing master"],
  openGraph: {
    title: "Swing Master — AI 골프 스윙 분석",
    description: "AI가 분석한 나만의 골프 스윙 교정 피드백",
    type: "website",
  },
};

import ReactQueryProvider from "@/components/providers/ReactQueryProvider";
import { AuthProvider } from "@/context/AuthContext";
import AppShell from "@/components/layout/AppShell";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <ReactQueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
