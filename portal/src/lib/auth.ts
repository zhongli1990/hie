/**
 * Auth API helper functions for HIE Portal
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:9302";

export interface User {
  id: string;
  tenant_id: string | null;
  email: string;
  display_name: string;
  mobile: string | null;
  title: string | null;
  department: string | null;
  avatar_url: string | null;
  status: string;
  role_id: string;
  role_name: string | null;
  created_at: string;
  approved_at: string | null;
  last_login_at: string | null;
  mfa_enabled: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterData {
  email: string;
  password: string;
  display_name: string;
  mobile?: string;
  title?: string;
  department?: string;
}

const TOKEN_KEY = "hie-token";
const USER_KEY = "hie-user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

export function setStoredUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(error.detail || "Login failed");
  }

  const data: LoginResponse = await res.json();
  setToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function register(data: RegisterData): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(error.detail || "Registration failed");
  }

  return res.json();
}

export async function getMe(): Promise<User | null> {
  const token = getToken();
  if (!token) return null;

  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    if (res.status === 401) {
      removeToken();
    }
    return null;
  }

  const user = await res.json();
  setStoredUser(user);
  return user;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/auth/change-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to change password" }));
    throw new Error(error.detail || "Failed to change password");
  }
}

export function logout(): void {
  removeToken();
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// Admin API functions
export async function fetchUsers(statusFilter?: string): Promise<User[]> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const url = statusFilter && statusFilter !== "all"
    ? `${API_BASE}/api/admin/users?status=${statusFilter}`
    : `${API_BASE}/api/admin/users`;

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to fetch users" }));
    throw new Error(error.detail || "Failed to fetch users");
  }

  return res.json();
}

export async function approveUser(userId: string): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to approve user" }));
    throw new Error(error.detail || "Failed to approve user");
  }

  return res.json();
}

export async function rejectUser(userId: string): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/reject`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to reject user" }));
    throw new Error(error.detail || "Failed to reject user");
  }

  return res.json();
}

export async function activateUser(userId: string): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/activate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to activate user" }));
    throw new Error(error.detail || "Failed to activate user");
  }

  return res.json();
}

export async function deactivateUser(userId: string): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/deactivate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to deactivate user" }));
    throw new Error(error.detail || "Failed to deactivate user");
  }

  return res.json();
}

export async function unlockUser(userId: string): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/unlock`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to unlock user" }));
    throw new Error(error.detail || "Failed to unlock user");
  }

  return res.json();
}

export interface Role {
  id: string;
  tenant_id: string | null;
  name: string;
  display_name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export async function fetchRoles(): Promise<Role[]> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/admin/roles`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to fetch roles" }));
    throw new Error(error.detail || "Failed to fetch roles");
  }

  return res.json();
}
