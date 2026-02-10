/**
 * OpenLI HIE - Healthcare Integration Engine
 * Copyright (c) 2026 Lightweight Integration Ltd
 * 
 * This file is part of OpenLI HIE.
 * Licensed under AGPL-3.0 (community) or Commercial license.
 * See LICENSE file for details.
 * 
 * Contact: zhong@li-ai.co.uk
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Network,
  MessageSquare,
  Settings,
  Activity,
  AlertTriangle,
  FileText,
  Users,
  GitBranch,
  ChevronLeft,
  ChevronRight,
  Bot,
  MessagesSquare,
  BookOpen,
  Webhook,
  Sparkles,
} from "lucide-react";
import { VERSION } from "./AboutModal";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: Network },
  { href: "/configure", label: "Configure", icon: GitBranch },
  { href: "/messages", label: "Messages", icon: MessageSquare },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/errors", label: "Errors", icon: AlertTriangle },
  { href: "/logs", label: "Logs", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

const agentItems = [
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/prompts", label: "Prompts", icon: Sparkles },
];

const adminItems = [
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/skills", label: "Skills", icon: BookOpen },
  { href: "/admin/hooks", label: "Hooks", icon: Webhook },
];

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div className={`flex h-full flex-col p-4 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      {/* Logo */}
      <div className="mb-6">
        <button
          onClick={onToggle}
          className="flex items-center gap-2 w-full text-left hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-md p-1 -m-1 transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-nhs-blue via-nhs-bright-blue to-nhs-light-blue flex-shrink-0">
            <span className="text-white text-sm font-bold">LI</span>
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">OpenLI HIE</div>
              <div className="text-[10px] text-gray-500 dark:text-gray-400">Healthcare Integration Engine</div>
            </div>
          )}
          {!collapsed && (
            <ChevronLeft className="h-4 w-4 ml-auto text-gray-400" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1">
        {!collapsed && <div className="px-3 pb-2 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Main</div>}
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-nhs-blue dark:bg-cyan-600 text-white"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700 hover:text-gray-900 dark:hover:text-white"
              }`}
              title={item.label}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* GenAI Agent Section */}
        <div className="my-2 border-t border-gray-200 dark:border-zinc-700" />
        {!collapsed && <div className="px-3 pb-2 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">GenAI</div>}
        {agentItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-nhs-blue dark:bg-cyan-600 text-white"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700 hover:text-gray-900 dark:hover:text-white"
              }`}
              title={item.label}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {adminItems.length > 0 && (
          <>
            <div className="my-2 border-t border-gray-200 dark:border-zinc-700" />
            {!collapsed && <div className="px-3 pb-2 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Admin</div>}
            {adminItems.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-nhs-blue dark:bg-cyan-600 text-white"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700 hover:text-gray-900 dark:hover:text-white"
                  }`}
                  title={item.label}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="mt-auto border-t border-gray-200 dark:border-zinc-700 pt-4">
        <div className="rounded-lg bg-gray-50 dark:bg-zinc-700 p-3">
          {!collapsed ? (
            <>
              <div className="text-xs font-medium text-gray-900 dark:text-white">OpenLI HIE v{VERSION}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Healthcare Integration Engine</div>
            </>
          ) : (
            <div className="text-xs font-medium text-gray-900 dark:text-white text-center">v{VERSION}</div>
          )}
        </div>
      </div>
    </div>
  );
}
