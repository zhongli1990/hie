"use client";

import { useState } from "react";
import {
  Bell,
  Database,
  Globe,
  Key,
  Mail,
  Save,
  Server,
  Shield,
  User,
} from "lucide-react";

interface SettingsSection {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const sections: SettingsSection[] = [
  { id: "general", label: "General", icon: Globe },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "database", label: "Database", icon: Database },
  { id: "api", label: "API Keys", icon: Key },
  { id: "email", label: "Email", icon: Mail },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("general");
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    siteName: "HIE Portal",
    siteUrl: "http://localhost:9303",
    timezone: "Europe/London",
    dateFormat: "DD/MM/YYYY",
    defaultProduction: "NHS-ADT-Integration",
    emailNotifications: true,
    slackNotifications: false,
    errorAlerts: true,
    performanceAlerts: true,
    dailyDigest: false,
    sessionTimeout: 30,
    mfaEnabled: false,
    ipWhitelist: "",
    auditLogging: true,
    dbHost: "localhost",
    dbPort: "9310",
    dbName: "hie",
    redisHost: "localhost",
    redisPort: "9311",
    smtpHost: "",
    smtpPort: "587",
    smtpUser: "",
    fromEmail: "noreply@hie.nhs.uk",
  });

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 1000));
    setSaving(false);
  };

  const updateSetting = (key: string, value: string | boolean | number) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">Manage system configuration and preferences</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue disabled:opacity-50"
        >
          <Save className={`h-4 w-4 ${saving ? "animate-spin" : ""}`} />
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-56 shrink-0">
          <nav className="space-y-1">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    activeSection === section.id
                      ? "bg-nhs-blue text-white"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {section.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {activeSection === "general" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">General Settings</h2>
                <p className="text-sm text-gray-500">Basic configuration for the HIE Portal</p>
              </div>
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Site Name</label>
                  <input
                    type="text"
                    value={settings.siteName}
                    onChange={(e) => updateSetting("siteName", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Site URL</label>
                  <input
                    type="text"
                    value={settings.siteUrl}
                    onChange={(e) => updateSetting("siteUrl", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Timezone</label>
                  <select
                    value={settings.timezone}
                    onChange={(e) => updateSetting("timezone", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  >
                    <option value="Europe/London">Europe/London (GMT)</option>
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Date Format</label>
                  <select
                    value={settings.dateFormat}
                    onChange={(e) => updateSetting("dateFormat", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  >
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                    <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Default Production</label>
                  <select
                    value={settings.defaultProduction}
                    onChange={(e) => updateSetting("defaultProduction", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  >
                    <option value="NHS-ADT-Integration">NHS-ADT-Integration</option>
                    <option value="Lab-Results-Feed">Lab-Results-Feed</option>
                    <option value="Radiology-Orders">Radiology-Orders</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Notification Settings</h2>
                <p className="text-sm text-gray-500">Configure how you receive alerts and updates</p>
              </div>
              <div className="space-y-4">
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Email Notifications</p>
                    <p className="text-xs text-gray-500">Receive notifications via email</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.emailNotifications}
                    onChange={(e) => updateSetting("emailNotifications", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Error Alerts</p>
                    <p className="text-xs text-gray-500">Get notified when errors occur</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.errorAlerts}
                    onChange={(e) => updateSetting("errorAlerts", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Performance Alerts</p>
                    <p className="text-xs text-gray-500">Get notified about performance issues</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.performanceAlerts}
                    onChange={(e) => updateSetting("performanceAlerts", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Daily Digest</p>
                    <p className="text-xs text-gray-500">Receive a daily summary email</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.dailyDigest}
                    onChange={(e) => updateSetting("dailyDigest", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
              </div>
            </div>
          )}

          {activeSection === "security" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Security Settings</h2>
                <p className="text-sm text-gray-500">Configure security and access controls</p>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Session Timeout (minutes)</label>
                  <input
                    type="number"
                    value={settings.sessionTimeout}
                    onChange={(e) => updateSetting("sessionTimeout", parseInt(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Multi-Factor Authentication</p>
                    <p className="text-xs text-gray-500">Require MFA for all users</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.mfaEnabled}
                    onChange={(e) => updateSetting("mfaEnabled", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Audit Logging</p>
                    <p className="text-xs text-gray-500">Log all user actions</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.auditLogging}
                    onChange={(e) => updateSetting("auditLogging", e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
                  />
                </label>
                <div>
                  <label className="block text-sm font-medium text-gray-700">IP Whitelist</label>
                  <textarea
                    value={settings.ipWhitelist}
                    onChange={(e) => updateSetting("ipWhitelist", e.target.value)}
                    placeholder="Enter IP addresses, one per line"
                    rows={4}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {activeSection === "database" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Database Settings</h2>
                <p className="text-sm text-gray-500">Configure database connections</p>
              </div>
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">PostgreSQL Host</label>
                  <input
                    type="text"
                    value={settings.dbHost}
                    onChange={(e) => updateSetting("dbHost", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">PostgreSQL Port</label>
                  <input
                    type="text"
                    value={settings.dbPort}
                    onChange={(e) => updateSetting("dbPort", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Database Name</label>
                  <input
                    type="text"
                    value={settings.dbName}
                    onChange={(e) => updateSetting("dbName", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div className="sm:col-span-2 border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-900">Redis</h3>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Redis Host</label>
                  <input
                    type="text"
                    value={settings.redisHost}
                    onChange={(e) => updateSetting("redisHost", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Redis Port</label>
                  <input
                    type="text"
                    value={settings.redisPort}
                    onChange={(e) => updateSetting("redisPort", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {activeSection === "api" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">API Keys</h2>
                <p className="text-sm text-gray-500">Manage API access tokens</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Production API Key</p>
                    <p className="mt-1 font-mono text-xs text-gray-500">hie_prod_****************************</p>
                  </div>
                  <button className="text-sm text-nhs-blue hover:underline">Regenerate</button>
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Development API Key</p>
                    <p className="mt-1 font-mono text-xs text-gray-500">hie_dev_*****************************</p>
                  </div>
                  <button className="text-sm text-nhs-blue hover:underline">Regenerate</button>
                </div>
              </div>
              <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <Key className="h-4 w-4" />
                Create New API Key
              </button>
            </div>
          )}

          {activeSection === "email" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Email Settings</h2>
                <p className="text-sm text-gray-500">Configure SMTP for sending emails</p>
              </div>
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">SMTP Host</label>
                  <input
                    type="text"
                    value={settings.smtpHost}
                    onChange={(e) => updateSetting("smtpHost", e.target.value)}
                    placeholder="smtp.example.com"
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">SMTP Port</label>
                  <input
                    type="text"
                    value={settings.smtpPort}
                    onChange={(e) => updateSetting("smtpPort", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">SMTP Username</label>
                  <input
                    type="text"
                    value={settings.smtpUser}
                    onChange={(e) => updateSetting("smtpUser", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">From Email</label>
                  <input
                    type="email"
                    value={settings.fromEmail}
                    onChange={(e) => updateSetting("fromEmail", e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
                  />
                </div>
              </div>
              <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <Mail className="h-4 w-4" />
                Send Test Email
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
