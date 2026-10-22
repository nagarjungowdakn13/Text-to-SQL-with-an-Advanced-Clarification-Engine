import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "QueryPilot — Intelligent Text-to-SQL & Ambiguity Resolution",
  description: "A production-grade Text-to-SQL platform featuring an advanced Clarification Engine, SQL Validation, Query Safety layers, and business semantic definitions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="h-full bg-slate-50 text-slate-900 font-sans antialiased">
        <div className="flex h-full min-h-screen overflow-hidden">
          {/* Sidebar */}
          <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0">
            {/* Brand Header */}
            <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
                QP
              </div>
              <div>
                <h1 className="font-bold text-base tracking-wide">QueryPilot</h1>
                <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Clarification Engine</p>
              </div>
            </div>

            {/* Sidebar Navigation Links */}
            <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
              <Link
                href="/workspace"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">💬</span>
                <span className="text-sm font-medium">Query Workspace</span>
              </Link>

              <Link
                href="/schema"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">📂</span>
                <span className="text-sm font-medium">Schema Explorer</span>
              </Link>

              <Link
                href="/semantics"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">🏷️</span>
                <span className="text-sm font-medium">Business Semantics</span>
              </Link>

              <Link
                href="/history"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">📜</span>
                <span className="text-sm font-medium">Audit History</span>
              </Link>

              <Link
                href="/evaluation"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">📊</span>
                <span className="text-sm font-medium">Evaluations</span>
              </Link>
              
              <Link
                href="/admin"
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-all duration-200 group"
              >
                <span className="text-slate-400 group-hover:text-blue-500 text-lg">⚙️</span>
                <span className="text-sm font-medium">Admin Settings</span>
              </Link>
            </nav>

            {/* Sidebar Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center text-sm font-semibold text-slate-300 border border-slate-700">
                  AD
                </div>
                <div>
                  <div className="text-xs font-semibold text-white">Administrator</div>
                  <div className="text-[10px] text-slate-500">admin@querypilot.com</div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Layout Area */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Topbar bar */}
            <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs font-semibold text-slate-500 tracking-wide uppercase">API status: connected</span>
              </div>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
                <div className="px-3 py-1 bg-slate-100 rounded-full border border-slate-200">
                  Engine: <span className="font-semibold text-slate-800">Mock LLM</span>
                </div>
                <div className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full border border-blue-100 font-semibold">
                  Role: Admin
                </div>
              </div>
            </header>

            {/* Scrollable page body */}
            <main className="flex-1 overflow-y-auto p-8">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
