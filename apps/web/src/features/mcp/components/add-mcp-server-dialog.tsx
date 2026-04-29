"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateMCPServer } from "../hooks/use-mcp-servers";

interface AddMCPServerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddMCPServerDialog({ open, onOpenChange }: AddMCPServerDialogProps) {
  const createServer = useCreateMCPServer();
  const [serverId, setServerId] = useState("");
  const [url, setUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createServer.mutate(
      {
        server_id: serverId,
        url,
        transport: "streamable-http",
      },
      {
        onSuccess: () => {
          setServerId("");
          setUrl("");
          onOpenChange(false);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add MCP Server Connection</DialogTitle>
            <DialogDescription>
              Configure a new Model Context Protocol server connection. The server will be
              automatically connected after creation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="server-id">Server ID</Label>
              <Input
                id="server-id"
                placeholder="e.g., github, slack, jira"
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                A unique identifier for this server (lowercase, no spaces)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">Server URL</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://mcp-server.example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                The HTTP endpoint for the MCP server
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createServer.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createServer.isPending}>
              {createServer.isPending ? "Adding..." : "Add Server"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
