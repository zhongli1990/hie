/**
 * SessionFilterPanel - Collapsible search/filter sidebar for message sessions
 * Provides comprehensive filtering capabilities for finding specific messages
 */

"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Filter, X } from "lucide-react";

export interface MessageFilters {
  dateFrom?: string;
  dateTo?: string;
  messageTypes?: string[];
  status?: "all" | "success" | "error" | "pending";
  items?: string[];
  sessionId?: string;
}

interface SessionFilterPanelProps {
  open: boolean;
  onToggle: () => void;
  filters: MessageFilters;
  onApply: (filters: MessageFilters) => void;
}

export function SessionFilterPanel({ open, onToggle, filters, onApply }: SessionFilterPanelProps) {
  const [localFilters, setLocalFilters] = useState<MessageFilters>(filters);

  function handleApply() {
    onApply(localFilters);
  }

  function handleReset() {
    setLocalFilters({});
    onApply({});
  }

  function toggleMessageType(type: string) {
    const types = localFilters.messageTypes || [];
    const newTypes = types.includes(type)
      ? types.filter((t) => t !== type)
      : [...types, type];

    setLocalFilters({ ...localFilters, messageTypes: newTypes });
  }

  return (
    <div
      className={`border-r bg-white transition-all duration-300 flex-shrink-0 ${
        open ? "w-80" : "w-12"
      }`}
    >
      {/* Collapse/Expand Button */}
      <button
        onClick={onToggle}
        className="w-full p-3 hover:bg-gray-100 flex items-center justify-center border-b transition-colors"
        title={open ? "Collapse filters" : "Expand filters"}
      >
        {open ? (
          <ChevronLeft className="h-5 w-5 text-gray-600" />
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Filter className="h-5 w-5 text-gray-600" />
            <span className="text-xs text-gray-500 font-medium">Filters</span>
          </div>
        )}
      </button>

      {open && (
        <div className="p-4 space-y-6 overflow-y-auto" style={{ height: "calc(100% - 60px)" }}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filters
            </h3>
            {Object.keys(localFilters).length > 0 && (
              <button
                onClick={handleReset}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Clear
              </button>
            )}
          </div>

          {/* Session ID Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Session ID
            </label>
            <input
              type="text"
              value={localFilters.sessionId || ""}
              onChange={(e) =>
                setLocalFilters({ ...localFilters, sessionId: e.target.value })
              }
              placeholder="Search by session ID..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date Range
            </label>
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-600 mb-1">From</label>
                <input
                  type="date"
                  value={localFilters.dateFrom || ""}
                  onChange={(e) =>
                    setLocalFilters({ ...localFilters, dateFrom: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">To</label>
                <input
                  type="date"
                  value={localFilters.dateTo || ""}
                  onChange={(e) =>
                    setLocalFilters({ ...localFilters, dateTo: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          {/* Message Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Message Type
            </label>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {[
                "ADT^A01",
                "ADT^A02",
                "ADT^A03",
                "ADT^A04",
                "ADT^A08",
                "ORU^R01",
                "ORM^O01",
                "SIU^S12",
                "MDM^T02",
                "DFT^P03",
              ].map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1.5 rounded"
                >
                  <input
                    type="checkbox"
                    checked={localFilters.messageTypes?.includes(type) || false}
                    onChange={() => toggleMessageType(type)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="font-mono text-xs">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <div className="space-y-2">
              {(["all", "success", "error", "pending"] as const).map((status) => (
                <label
                  key={status}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 p-1.5 rounded"
                >
                  <input
                    type="radio"
                    name="status"
                    value={status}
                    checked={localFilters.status === status || (!localFilters.status && status === "all")}
                    onChange={(e) =>
                      setLocalFilters({ ...localFilters, status: e.target.value as any })
                    }
                    className="border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="capitalize flex items-center gap-1.5">
                    {status === "success" && <span className="text-green-600">✓</span>}
                    {status === "error" && <span className="text-red-600">✗</span>}
                    {status === "pending" && <span className="text-yellow-600">⏳</span>}
                    {status}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="sticky bottom-0 pt-4 pb-2 bg-white border-t space-y-2">
            <button
              onClick={handleApply}
              className="w-full px-4 py-2.5 bg-nhs-blue text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors shadow-sm flex items-center justify-center gap-2"
            >
              <Filter className="h-4 w-4" />
              Apply Filters
            </button>
            <button
              onClick={handleReset}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <X className="h-4 w-4" />
              Reset All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
