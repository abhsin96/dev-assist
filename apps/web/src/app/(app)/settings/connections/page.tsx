"use client";

import { MCPConnectionsList } from "@/features/mcp/components/mcp-connections-list";

export default function ConnectionsPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">MCP Connections</h1>
        <p className="text-muted-foreground mt-2">
          Manage Model Context Protocol server connections and control what tools agents can use.
        </p>
      </div>
      <MCPConnectionsList />
    </div>
  );
}
