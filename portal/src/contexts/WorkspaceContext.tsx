'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { listWorkspaces, type Workspace } from '@/lib/api-v2';

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  error: string | null;
  setCurrentWorkspace: (workspace: Workspace) => void;
  refreshWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

const WORKSPACE_STORAGE_KEY = 'hie_current_workspace_id';

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshWorkspaces = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await listWorkspaces();
      setWorkspaces(response.workspaces);
      
      // Restore previously selected workspace or select default
      const savedWorkspaceId = localStorage.getItem(WORKSPACE_STORAGE_KEY);
      const savedWorkspace = response.workspaces.find(w => w.id === savedWorkspaceId);
      const defaultWorkspace = response.workspaces.find(w => w.name === 'default');
      
      if (savedWorkspace) {
        setCurrentWorkspaceState(savedWorkspace);
      } else if (defaultWorkspace) {
        setCurrentWorkspaceState(defaultWorkspace);
      } else if (response.workspaces.length > 0) {
        setCurrentWorkspaceState(response.workspaces[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workspaces');
      console.error('Failed to load workspaces:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshWorkspaces();
  }, [refreshWorkspaces]);

  const setCurrentWorkspace = useCallback((workspace: Workspace) => {
    setCurrentWorkspaceState(workspace);
    localStorage.setItem(WORKSPACE_STORAGE_KEY, workspace.id);
  }, []);

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        currentWorkspace,
        isLoading,
        error,
        setCurrentWorkspace,
        refreshWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
