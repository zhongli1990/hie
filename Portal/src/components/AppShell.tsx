"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import { ThemeProvider } from "./ThemeProvider";

export default function AppShell({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gray-50 dark:bg-zinc-900">
        <div className="flex min-h-screen">
          {/* Desktop Sidebar */}
          <aside
            className={`hidden md:block border-r border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 transition-all duration-300 flex-shrink-0 ${
              sidebarCollapsed ? "w-16" : "w-64"
            }`}
          >
            <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
          </aside>

          {/* Mobile Sidebar Overlay */}
          {mobileMenuOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
          )}

          {/* Mobile Sidebar */}
          <aside
            className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-zinc-800 border-r border-gray-200 dark:border-zinc-700 transform transition-transform duration-300 md:hidden ${
              mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar collapsed={false} onToggle={() => setMobileMenuOpen(false)} />
          </aside>

          <div className="flex min-w-0 flex-1 flex-col">
            <header className="border-b border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800">
              <TopNav />
            </header>
            <main className="flex-1 overflow-auto p-6">
              <div className="mx-auto w-full max-w-7xl">{children}</div>
            </main>
          </div>
        </div>
      </div>
    </ThemeProvider>
  );
}
