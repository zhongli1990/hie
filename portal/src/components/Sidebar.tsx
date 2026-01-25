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
} from "lucide-react";

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

const adminItems = [
  { href: "/admin/users", label: "Users", icon: Users },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col p-4">
      {/* Logo */}
      <div className="mb-8 px-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-nhs-blue">
            <span className="text-sm font-bold text-white">H</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">HIE Portal</div>
            <div className="text-xs text-gray-500">Integration Engine</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1">
        <div className="px-3 pb-2 text-xs font-medium uppercase text-gray-500">
          Main
        </div>
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-nhs-blue text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}

        <div className="mt-6 px-3 pb-2 text-xs font-medium uppercase text-gray-500">
          Admin
        </div>
        {adminItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-nhs-blue text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto border-t border-gray-200 pt-4">
        <div className="rounded-lg bg-gray-50 p-3">
          <div className="text-xs font-medium text-gray-900">HIE v0.1.0</div>
          <div className="text-xs text-gray-500">Healthcare Integration Engine</div>
        </div>
      </div>
    </div>
  );
}
