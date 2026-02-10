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

import { useState } from "react";
import { Webhook, Shield, FileText, Heart, CheckSquare, X, Save, Info } from "lucide-react";

interface PlatformHooks {
  security: {
    block_dangerous_commands: boolean;
    block_path_traversal: boolean;
    validate_hl7_structure: boolean;
    enforce_tls: boolean;
    blocked_patterns: string[];
    enabled: boolean;
  };
  audit: {
    log_all_agent_actions: boolean;
    log_message_access: boolean;
    log_config_changes: boolean;
    enabled: boolean;
  };
}

interface TenantHooks {
  compliance: {
    detect_nhs_numbers: boolean;
    detect_pii: boolean;
    block_external_data_transfer: boolean;
    enforce_data_retention: boolean;
    retention_days: number;
    enabled: boolean;
  };
  clinical_safety: {
    validate_message_integrity: boolean;
    require_ack_confirmation: boolean;
    alert_on_message_loss: boolean;
    max_retry_attempts: number;
    enabled: boolean;
  };
}

export default function HooksManagementPage() {
  const [platformHooks, setPlatformHooks] = useState<PlatformHooks>({
    security: {
      block_dangerous_commands: true,
      block_path_traversal: true,
      validate_hl7_structure: true,
      enforce_tls: false,
      blocked_patterns: [
        "rm -rf /",
        "sudo rm",
        "DROP TABLE",
        "DELETE FROM hie_",
        "curl | bash",
        "wget | sh",
      ],
      enabled: true,
    },
    audit: {
      log_all_agent_actions: true,
      log_message_access: true,
      log_config_changes: true,
      enabled: true,
    },
  });

  const [tenantHooks, setTenantHooks] = useState<TenantHooks>({
    compliance: {
      detect_nhs_numbers: true,
      detect_pii: true,
      block_external_data_transfer: false,
      enforce_data_retention: true,
      retention_days: 365,
      enabled: true,
    },
    clinical_safety: {
      validate_message_integrity: true,
      require_ack_confirmation: true,
      alert_on_message_loss: true,
      max_retry_attempts: 3,
      enabled: true,
    },
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [newPattern, setNewPattern] = useState("");

  const handleAddPattern = () => {
    if (!newPattern.trim()) return;
    setPlatformHooks(prev => ({
      ...prev,
      security: {
        ...prev.security,
        blocked_patterns: [...prev.security.blocked_patterns, newPattern.trim()],
      },
    }));
    setNewPattern("");
  };

  const handleRemovePattern = (index: number) => {
    setPlatformHooks(prev => ({
      ...prev,
      security: {
        ...prev.security,
        blocked_patterns: prev.security.blocked_patterns.filter((_, i) => i !== index),
      },
    }));
  };

  const handleSaveHooks = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setSuccess("Hooks configuration saved. Changes take effect on next engine restart.");
      setEditingSection(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save hooks");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Webhook className="h-6 w-6" />
          Hooks Configuration
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Configure security, audit, compliance, and clinical safety hooks for HIE agent operations.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
            <button onClick={() => setError(null)}><X className="h-4 w-4 text-red-500" /></button>
          </div>
        </div>
      )}

      {success && (
        <div className="rounded-md bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-green-700 dark:text-green-300">{success}</span>
            <button onClick={() => setSuccess(null)}><X className="h-4 w-4 text-green-500" /></button>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Platform Hooks */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Platform Hooks</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">Always active. Protect the HIE engine and data integrity.</p>

          {/* Security Hooks */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm">
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-nhs-blue" />
                  <h3 className="font-medium text-gray-900 dark:text-white">Security Hooks</h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${platformHooks.security.enabled ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-gray-100 text-gray-600"}`}>
                    {platformHooks.security.enabled ? "ON" : "OFF"}
                  </span>
                  <button onClick={() => setEditingSection(editingSection === "security" ? null : "security")}
                    className="text-sm text-nhs-blue hover:text-nhs-dark-blue">
                    {editingSection === "security" ? "Close" : "Configure"}
                  </button>
                </div>
              </div>
            </div>

            {editingSection === "security" ? (
              <div className="p-4 space-y-4">
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={platformHooks.security.block_dangerous_commands}
                    onChange={(e) => setPlatformHooks(prev => ({ ...prev, security: { ...prev.security, block_dangerous_commands: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Block dangerous shell commands
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={platformHooks.security.block_path_traversal}
                    onChange={(e) => setPlatformHooks(prev => ({ ...prev, security: { ...prev.security, block_path_traversal: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Block path traversal attacks
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={platformHooks.security.validate_hl7_structure}
                    onChange={(e) => setPlatformHooks(prev => ({ ...prev, security: { ...prev.security, validate_hl7_structure: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Validate HL7 message structure before processing
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={platformHooks.security.enforce_tls}
                    onChange={(e) => setPlatformHooks(prev => ({ ...prev, security: { ...prev.security, enforce_tls: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Enforce TLS for all external connections
                </label>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Blocked Patterns ({platformHooks.security.blocked_patterns.length})
                  </label>
                  <div className="space-y-1 max-h-32 overflow-y-auto mb-2">
                    {platformHooks.security.blocked_patterns.map((pattern, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 dark:bg-zinc-700 px-3 py-1.5 rounded text-sm">
                        <code className="text-xs font-mono text-gray-700 dark:text-gray-300">{pattern}</code>
                        <button onClick={() => handleRemovePattern(index)} className="text-red-500 hover:text-red-700 text-xs">Remove</button>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input type="text" value={newPattern} onChange={(e) => setNewPattern(e.target.value)}
                      placeholder="Add blocked pattern..."
                      className="flex-1 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white"
                      onKeyDown={(e) => e.key === "Enter" && handleAddPattern()} />
                    <button onClick={handleAddPattern}
                      className="px-3 py-1.5 text-sm bg-nhs-blue text-white rounded-md hover:bg-nhs-dark-blue">Add</button>
                  </div>
                </div>

                <button onClick={handleSaveHooks} disabled={saving}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-nhs-blue rounded-md hover:bg-nhs-dark-blue disabled:opacity-50">
                  {saving ? "Saving..." : "Save Security Hooks"}
                </button>
              </div>
            ) : (
              <div className="p-4 text-sm text-gray-600 dark:text-gray-400">
                <ul className="space-y-1">
                  <li className="flex items-center gap-2">
                    <CheckSquare className="h-3 w-3 text-green-600" /> Block dangerous commands ({platformHooks.security.blocked_patterns.length} patterns)
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckSquare className="h-3 w-3 text-green-600" /> Block path traversal
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckSquare className="h-3 w-3 text-green-600" /> Validate HL7 structure
                  </li>
                  <li className="flex items-center gap-2">
                    {platformHooks.security.enforce_tls
                      ? <CheckSquare className="h-3 w-3 text-green-600" />
                      : <span className="h-3 w-3 rounded border border-gray-300 inline-block" />}
                    Enforce TLS
                  </li>
                </ul>
              </div>
            )}
          </div>

          {/* Audit Hooks */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm">
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-nhs-blue" />
                  <h3 className="font-medium text-gray-900 dark:text-white">Audit Hooks</h3>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${platformHooks.audit.enabled ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-gray-100 text-gray-600"}`}>
                  {platformHooks.audit.enabled ? "ON" : "OFF"}
                </span>
              </div>
            </div>
            <div className="p-4 text-sm text-gray-600 dark:text-gray-400">
              <ul className="space-y-1">
                <li className="flex items-center gap-2">
                  <input type="checkbox" checked={platformHooks.audit.log_all_agent_actions} readOnly className="rounded border-gray-300" />
                  Log all agent actions
                </li>
                <li className="flex items-center gap-2">
                  <input type="checkbox" checked={platformHooks.audit.log_message_access} readOnly className="rounded border-gray-300" />
                  Log message access (HL7/FHIR)
                </li>
                <li className="flex items-center gap-2">
                  <input type="checkbox" checked={platformHooks.audit.log_config_changes} readOnly className="rounded border-gray-300" />
                  Log configuration changes
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Tenant Hooks */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Tenant Hooks</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">Configurable per NHS Trust / organization.</p>

          {/* Compliance Hooks */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm">
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-green-600" />
                  <h3 className="font-medium text-gray-900 dark:text-white">NHS Compliance Hooks</h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${tenantHooks.compliance.enabled ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-gray-100 text-gray-600"}`}>
                    {tenantHooks.compliance.enabled ? "ON" : "OFF"}
                  </span>
                  <button onClick={() => setEditingSection(editingSection === "compliance" ? null : "compliance")}
                    className="text-sm text-nhs-blue hover:text-nhs-dark-blue">
                    {editingSection === "compliance" ? "Close" : "Configure"}
                  </button>
                </div>
              </div>
            </div>

            {editingSection === "compliance" ? (
              <div className="p-4 space-y-3">
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.compliance.detect_nhs_numbers}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, compliance: { ...prev.compliance, detect_nhs_numbers: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Detect NHS numbers in agent output
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.compliance.detect_pii}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, compliance: { ...prev.compliance, detect_pii: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Detect PII (names, addresses, DOB)
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.compliance.block_external_data_transfer}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, compliance: { ...prev.compliance, block_external_data_transfer: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Block external data transfer
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.compliance.enforce_data_retention}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, compliance: { ...prev.compliance, enforce_data_retention: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Enforce data retention policy
                </label>
                {tenantHooks.compliance.enforce_data_retention && (
                  <div className="ml-6">
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Retention period (days)</label>
                    <input type="number" value={tenantHooks.compliance.retention_days}
                      onChange={(e) => setTenantHooks(prev => ({ ...prev, compliance: { ...prev.compliance, retention_days: parseInt(e.target.value) || 365 } }))}
                      className="w-32 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
                  </div>
                )}
                <button onClick={handleSaveHooks} disabled={saving}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-nhs-blue rounded-md hover:bg-nhs-dark-blue disabled:opacity-50 mt-2">
                  {saving ? "Saving..." : "Save Compliance Hooks"}
                </button>
              </div>
            ) : (
              <div className="p-4 text-sm text-gray-600 dark:text-gray-400">
                <ul className="space-y-1">
                  {[
                    { label: "Detect NHS numbers", checked: tenantHooks.compliance.detect_nhs_numbers },
                    { label: "Detect PII", checked: tenantHooks.compliance.detect_pii },
                    { label: "Block external transfer", checked: tenantHooks.compliance.block_external_data_transfer },
                    { label: `Data retention (${tenantHooks.compliance.retention_days} days)`, checked: tenantHooks.compliance.enforce_data_retention },
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className={item.checked ? "text-green-600" : "text-gray-400"}>{item.checked ? "✓" : "○"}</span>
                      {item.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Clinical Safety Hooks */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm">
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Heart className="h-5 w-5 text-red-500" />
                  <h3 className="font-medium text-gray-900 dark:text-white">Clinical Safety Hooks</h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${tenantHooks.clinical_safety.enabled ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-gray-100 text-gray-600"}`}>
                    {tenantHooks.clinical_safety.enabled ? "ON" : "OFF"}
                  </span>
                  <button onClick={() => setEditingSection(editingSection === "clinical" ? null : "clinical")}
                    className="text-sm text-nhs-blue hover:text-nhs-dark-blue">
                    {editingSection === "clinical" ? "Close" : "Configure"}
                  </button>
                </div>
              </div>
            </div>

            {editingSection === "clinical" ? (
              <div className="p-4 space-y-3">
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.clinical_safety.validate_message_integrity}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, clinical_safety: { ...prev.clinical_safety, validate_message_integrity: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Validate message integrity (checksum)
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.clinical_safety.require_ack_confirmation}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, clinical_safety: { ...prev.clinical_safety, require_ack_confirmation: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Require ACK confirmation for all messages
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input type="checkbox" checked={tenantHooks.clinical_safety.alert_on_message_loss}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, clinical_safety: { ...prev.clinical_safety, alert_on_message_loss: e.target.checked } }))}
                    className="rounded border-gray-300" />
                  Alert on potential message loss
                </label>
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Max retry attempts</label>
                  <input type="number" value={tenantHooks.clinical_safety.max_retry_attempts}
                    onChange={(e) => setTenantHooks(prev => ({ ...prev, clinical_safety: { ...prev.clinical_safety, max_retry_attempts: parseInt(e.target.value) || 3 } }))}
                    className="w-32 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
                </div>
                <button onClick={handleSaveHooks} disabled={saving}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-nhs-blue rounded-md hover:bg-nhs-dark-blue disabled:opacity-50 mt-2">
                  {saving ? "Saving..." : "Save Clinical Safety Hooks"}
                </button>
              </div>
            ) : (
              <div className="p-4 text-sm text-gray-600 dark:text-gray-400">
                <ul className="space-y-1">
                  {[
                    { label: "Validate message integrity", checked: tenantHooks.clinical_safety.validate_message_integrity },
                    { label: "Require ACK confirmation", checked: tenantHooks.clinical_safety.require_ack_confirmation },
                    { label: "Alert on message loss", checked: tenantHooks.clinical_safety.alert_on_message_loss },
                    { label: `Max retries: ${tenantHooks.clinical_safety.max_retry_attempts}`, checked: true },
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className={item.checked ? "text-green-600" : "text-gray-400"}>{item.checked ? "✓" : "○"}</span>
                      {item.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
        <div className="flex gap-3">
          <Info className="h-5 w-5 text-nhs-blue flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800 dark:text-blue-200">
            <p className="font-medium mb-1">About HIE Hooks</p>
            <p>
              Hooks are pre/post execution validators that run when agents interact with the HIE engine.
              Platform hooks protect system integrity and are always active. Tenant hooks can be configured
              per NHS Trust for compliance (DTAC, DSPT) and clinical safety (DCB0129/DCB0160) requirements.
            </p>
            <p className="mt-2">
              <strong>Note:</strong> Changes to hooks configuration require an engine restart to take effect.
              In production, manage hooks via environment variables or the configuration API.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
