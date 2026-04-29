"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export interface MCPServerInfo {
  server_id: string;
  url: string;
  connected: boolean;
  enabled: boolean;
  tool_count: number;
  tools: string[];
  error_code?: string;
  error_message?: string;
  last_connected_at?: string;
}

export interface MCPServerCreate {
  server_id: string;
  url: string;
  transport?: "streamable-http";
  config?: Record<string, unknown>;
}

export interface MCPServerUpdate {
  url?: string;
  enabled?: boolean;
  config?: Record<string, unknown>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export function useMCPServers() {
  return useQuery<MCPServerInfo[]>({
    queryKey: ["mcp-servers"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/mcp/servers`, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to fetch MCP servers");
      }
      return response.json();
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useCreateMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (server: MCPServerCreate) => {
      const response = await fetch(`${API_BASE}/api/mcp/servers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(server),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to create MCP server");
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("MCP server added successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to add MCP server: ${error.message}`);
    },
  });
}

export function useUpdateMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      server_id,
      updates,
    }: {
      server_id: string;
      updates: MCPServerUpdate;
    }) => {
      const response = await fetch(`${API_BASE}/api/mcp/servers/${server_id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(updates),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to update MCP server");
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("MCP server updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update MCP server: ${error.message}`);
    },
  });
}

export function useDeleteMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (server_id: string) => {
      const response = await fetch(`${API_BASE}/api/mcp/servers/${server_id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to delete MCP server");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("MCP server deleted successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete MCP server: ${error.message}`);
    },
  });
}

export function useReconnectMCPServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (server_id: string) => {
      const response = await fetch(`${API_BASE}/api/mcp/servers/${server_id}/reconnect`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to reconnect to MCP server");
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("Reconnection attempt completed");
    },
    onError: (error: Error) => {
      toast.error(`Failed to reconnect: ${error.message}`);
    },
  });
}
