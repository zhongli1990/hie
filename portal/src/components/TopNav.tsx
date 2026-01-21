"use client";

import { Bell, Search, User } from "lucide-react";

export default function TopNav() {
  return (
    <div className="flex h-14 items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search productions, messages..."
            className="h-9 w-80 rounded-lg border border-gray-200 bg-gray-50 pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
        </button>

        <div className="flex items-center gap-3 rounded-lg border border-gray-200 px-3 py-1.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-nhs-blue">
            <User className="h-4 w-4 text-white" />
          </div>
          <div className="text-sm">
            <div className="font-medium text-gray-900">Admin User</div>
            <div className="text-xs text-gray-500">admin@nhs.uk</div>
          </div>
        </div>
      </div>
    </div>
  );
}
