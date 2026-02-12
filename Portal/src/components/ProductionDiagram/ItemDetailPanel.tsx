/**
 * Right-side detail panel for topology items
 * Shows detailed configuration, events, messages, and metrics
 */

"use client";

import { useState } from "react";
import { X, Settings, Activity, MessageSquare, BarChart3 } from "lucide-react";
import type { ProjectItem } from "./types";

interface ItemDetailPanelProps {
  item: ProjectItem | null;
  onClose: () => void;
}

type TabType = "config" | "events" | "messages" | "metrics";

export function ItemDetailPanel({ item, onClose }: ItemDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("config");

  if (!item) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Slide-in Panel */}
      <div
        className="fixed right-0 top-0 bottom-0 w-[400px] bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right"
        style={{
          animation: "slideInRight 300ms ease-out",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate" title={item.name}>
              {item.name}
            </h2>
            <p className="text-sm text-gray-500 truncate" title={item.class_name}>
              {item.class_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Close panel"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b bg-white">
          <TabButton
            icon={<Settings className="h-4 w-4" />}
            label="Config"
            active={activeTab === "config"}
            onClick={() => setActiveTab("config")}
          />
          <TabButton
            icon={<Activity className="h-4 w-4" />}
            label="Events"
            active={activeTab === "events"}
            onClick={() => setActiveTab("events")}
          />
          <TabButton
            icon={<MessageSquare className="h-4 w-4" />}
            label="Messages"
            active={activeTab === "messages"}
            onClick={() => setActiveTab("messages")}
          />
          <TabButton
            icon={<BarChart3 className="h-4 w-4" />}
            label="Metrics"
            active={activeTab === "metrics"}
            onClick={() => setActiveTab("metrics")}
          />
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "config" && <ConfigurationTab item={item} />}
          {activeTab === "events" && <EventsTab item={item} />}
          {activeTab === "messages" && <MessagesTab item={item} />}
          {activeTab === "metrics" && <MetricsTab item={item} />}
        </div>
      </div>

      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
      `}</style>
    </>
  );
}

interface TabButtonProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}

function TabButton({ icon, label, active, onClick }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
        ${
          active
            ? "border-nhs-blue text-nhs-blue bg-blue-50"
            : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
        }
      `}
    >
      {icon}
      {label}
    </button>
  );
}

// Placeholder tab components
function ConfigurationTab({ item }: { item: ProjectItem }) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">Basic Settings</h3>
        <div className="space-y-3">
          <SettingRow label="Type" value={item.item_type} />
          <SettingRow label="Enabled" value={item.enabled ? "Yes" : "No"} />
          <SettingRow label="Pool Size" value={item.pool_size.toString()} />
          <SettingRow label="Category" value={item.category || "-"} />
        </div>
      </div>

      {Object.keys(item.adapter_settings).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Adapter Settings</h3>
          <div className="space-y-2">
            {Object.entries(item.adapter_settings).map(([key, value]) => (
              <SettingRow key={key} label={key} value={String(value)} />
            ))}
          </div>
        </div>
      )}

      {Object.keys(item.host_settings).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Host Settings</h3>
          <div className="space-y-2">
            {Object.entries(item.host_settings).map(([key, value]) => (
              <SettingRow key={key} label={key} value={String(value)} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EventsTab({ item }: { item: ProjectItem }) {
  return (
    <div className="p-6">
      <div className="text-center py-12 text-gray-500">
        <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <p className="text-sm">Event logs will be displayed here</p>
        <p className="text-xs text-gray-400 mt-1">Coming in next phase</p>
      </div>
    </div>
  );
}

function MessagesTab({ item }: { item: ProjectItem }) {
  return (
    <div className="p-6">
      <div className="text-center py-12 text-gray-500">
        <MessageSquare className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <p className="text-sm">Message history will be displayed here</p>
        <p className="text-xs text-gray-400 mt-1">Coming in next phase</p>
      </div>
    </div>
  );
}

function MetricsTab({ item }: { item: ProjectItem }) {
  return (
    <div className="p-6">
      {item.metrics ? (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Runtime Metrics</h3>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(item.metrics).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-4">
                <p className="text-xs text-gray-600 uppercase mb-1">
                  {key.replace(/_/g, " ")}
                </p>
                <p className="text-2xl font-bold text-gray-900">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm">No metrics available</p>
          <p className="text-xs text-gray-400 mt-1">Metrics will appear when item is running</p>
        </div>
      )}
    </div>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start py-2 border-b border-gray-100">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-right max-w-[200px] truncate" title={value}>
        {value}
      </span>
    </div>
  );
}
