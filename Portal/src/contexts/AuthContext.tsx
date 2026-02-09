"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { User, getMe, login as apiLogin, logout as apiLogout, removeToken, getStoredUser } from "@/lib/auth";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await getMe();
      setUser(userData);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      // First try to get stored user for immediate display
      const storedUser = getStoredUser();
      if (storedUser) {
        setUser(storedUser);
      }
      // Then verify with server
      await refreshUser();
      setIsLoading(false);
    };
    checkAuth();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string): Promise<User> => {
    const response = await apiLogin(email, password);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user && user.status === "active",
    isAdmin: user?.role_name === "Tenant Administrator" || user?.role_name === "Super Administrator",
    isSuperAdmin: user?.role_name === "Super Administrator" || user?.tenant_id === null,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
