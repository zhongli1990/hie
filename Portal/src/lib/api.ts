/**
 * HIE API Client
 * 
 * Provides typed functions for interacting with the HIE Management API.
 */

import type {
  Production,
  Item,
  DashboardStats,
  SystemHealth,
  ProductionState,
} from "@/types";

const API_BASE = "/api";

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Unknown error" }));
    throw new APIError(response.status, error.error || error.message || "Request failed");
  }

  return response.json();
}

// Health & Stats

export async function getHealth(): Promise<{ status: string; version: string }> {
  return request("/health");
}

export async function getServiceHealth(): Promise<SystemHealth> {
  return request("/health/services");
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return request("/stats/dashboard");
}

// Productions

export async function listProductions(): Promise<Production[]> {
  return request("/productions");
}

export async function getProduction(name: string): Promise<Production> {
  return request(`/productions/${encodeURIComponent(name)}`);
}

export async function createProduction(data: Partial<Production>): Promise<{ status: string; name: string }> {
  return request("/productions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProduction(
  name: string,
  data: Partial<Production>
): Promise<{ status: string; name: string }> {
  return request(`/productions/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteProduction(name: string): Promise<{ status: string; name: string }> {
  return request(`/productions/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

// Production Actions

export async function startProduction(name: string): Promise<{ status: string; state: ProductionState }> {
  return request(`/productions/${encodeURIComponent(name)}/start`, {
    method: "POST",
  });
}

export async function stopProduction(name: string): Promise<{ status: string; state: ProductionState }> {
  return request(`/productions/${encodeURIComponent(name)}/stop`, {
    method: "POST",
  });
}

export async function pauseProduction(name: string): Promise<{ status: string; state: ProductionState }> {
  return request(`/productions/${encodeURIComponent(name)}/pause`, {
    method: "POST",
  });
}

export async function resumeProduction(name: string): Promise<{ status: string; state: ProductionState }> {
  return request(`/productions/${encodeURIComponent(name)}/resume`, {
    method: "POST",
  });
}

// Items

export async function listItems(productionName: string): Promise<Item[]> {
  return request(`/productions/${encodeURIComponent(productionName)}/items`);
}

export async function getItem(productionName: string, itemId: string): Promise<Item> {
  return request(`/productions/${encodeURIComponent(productionName)}/items/${encodeURIComponent(itemId)}`);
}

export async function startItem(productionName: string, itemId: string): Promise<{ status: string }> {
  return request(`/productions/${encodeURIComponent(productionName)}/items/${encodeURIComponent(itemId)}/start`, {
    method: "POST",
  });
}

export async function stopItem(productionName: string, itemId: string): Promise<{ status: string }> {
  return request(`/productions/${encodeURIComponent(productionName)}/items/${encodeURIComponent(itemId)}/stop`, {
    method: "POST",
  });
}

// Configuration

export async function exportConfig(productionName: string): Promise<object> {
  return request(`/productions/${encodeURIComponent(productionName)}/config`);
}

export async function importConfig(productionName: string, config: object): Promise<{ status: string }> {
  return request(`/productions/${encodeURIComponent(productionName)}/config`, {
    method: "POST",
    body: JSON.stringify(config),
  });
}

// Messages

export interface MessageSearchParams {
  source?: string;
  messageType?: string;
  state?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}

export async function searchMessages(params: MessageSearchParams = {}): Promise<object[]> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, String(value));
    }
  });
  
  const query = searchParams.toString();
  return request(`/messages${query ? `?${query}` : ""}`);
}

export async function getMessage(messageId: string): Promise<object> {
  return request(`/messages/${encodeURIComponent(messageId)}`);
}

export async function resendMessage(messageId: string): Promise<{ status: string }> {
  return request(`/messages/${encodeURIComponent(messageId)}/resend`, {
    method: "POST",
  });
}

// Export all functions
export const api = {
  getHealth,
  getServiceHealth,
  getDashboardStats,
  listProductions,
  getProduction,
  createProduction,
  updateProduction,
  deleteProduction,
  startProduction,
  stopProduction,
  pauseProduction,
  resumeProduction,
  listItems,
  getItem,
  startItem,
  stopItem,
  exportConfig,
  importConfig,
  searchMessages,
  getMessage,
  resendMessage,
};

export default api;
