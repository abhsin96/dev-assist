"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Plus, Power, RefreshCw, Trash2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  useMCPServers,
  useUpdateMCPServer,
  useDeleteMCPServer,
  useReconnectMCPServer,
  MCPServerInfo,
} from "../hooks/use-mcp-servers";
import { AddMCPServerDialog } from "./add-mcp-server-dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export function MCPConnectionsList() {
  const { data: servers, isLoading } = useMCPServers();
  const updateServer = useUpdateMCPServer();
  const deleteServer = useDeleteMCPServer();
  const reconnectServer = useReconnectMCPServer();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [serverToDelete, setServerToDelete] = useState<string | null>(null);

  const handleToggleEnabled = (server: MCPServerInfo) => {
    updateServer.mutate({
      server_id: server.server_id,
      updates: { enabled: !server.enabled },
    });
  };

  const handleReconnect = (serverId: string) => {
    reconnectServer.mutate(serverId);
  };

  const handleDeleteClick = (serverId: string) => {
    setServerToDelete(serverId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (serverToDelete) {
      deleteServer.mutate(serverToDelete);
      setServerToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const getStatusBadge = (server: MCPServerInfo) => {
    if (!server.enabled) {
      return (
        <Badge variant="secondary" className="gap-1">
          <Power className="h-3 w-3" />
          Disabled
        </Badge>
      );
    }
    if (server.error_code) {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Error
        </Badge>
      );
    }
    if (server.connected) {
      return (
        <Badge variant="default" className="gap-1 bg-green-600">
          <CheckCircle2 className="h-3 w-3" />
          Connected
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" className="gap-1">
        <AlertCircle className="h-3 w-3" />
        Disconnected
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button onClick={() => setAddDialogOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Connection
          </Button>
        </div>

        {servers && servers.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No MCP servers configured. Add your first connection to get started.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {servers?.map((server) => (
              <Card key={server.server_id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <CardTitle>{server.server_id}</CardTitle>
                        {getStatusBadge(server)}
                      </div>
                      <CardDescription className="font-mono text-xs">
                        {server.url}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={server.enabled}
                        onCheckedChange={() => handleToggleEnabled(server)}
                        disabled={updateServer.isPending}
                      />
                      {server.error_code && server.enabled && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReconnect(server.server_id)}
                          disabled={reconnectServer.isPending}
                          className="gap-2"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Reconnect
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(server.server_id)}
                        disabled={deleteServer.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {server.error_message && (
                    <div className="mb-4 rounded-md bg-destructive/10 p-3">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-destructive">
                            {server.error_code}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {server.error_message}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Tools exposed:</span>
                      <span className="font-medium">{server.tool_count}</span>
                    </div>
                    {server.tools.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {server.tools.map((tool) => (
                          <Badge key={tool} variant="outline" className="text-xs">
                            {tool}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {server.last_connected_at && (
                      <div className="text-xs text-muted-foreground">
                        Last connected: {new Date(server.last_connected_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <AddMCPServerDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete MCP Server</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this MCP server connection? This action cannot be
              undone. Agents will no longer be able to use tools from this server.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
