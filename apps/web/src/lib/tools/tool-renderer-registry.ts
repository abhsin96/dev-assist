/**
 * Tool Renderer Registry
 * Maps tool names to their corresponding React components for generative UI
 */

import { ComponentType } from "react";

export interface ToolRendererProps {
  toolName: string;
  toolCallId: string;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
  status: "loading" | "success" | "error";
  onRetry?: () => void;
}

type ToolRenderer = ComponentType<ToolRendererProps>;

class ToolRendererRegistry {
  private renderers = new Map<string, ToolRenderer>();

  /**
   * Register a tool renderer component
   */
  register(toolName: string, renderer: ToolRenderer): void {
    this.renderers.set(toolName, renderer);
  }

  /**
   * Get a renderer for a specific tool
   */
  get(toolName: string): ToolRenderer | undefined {
    return this.renderers.get(toolName);
  }

  /**
   * Check if a renderer exists for a tool
   */
  has(toolName: string): boolean {
    return this.renderers.has(toolName);
  }

  /**
   * Get all registered tool names
   */
  getRegisteredTools(): string[] {
    return Array.from(this.renderers.keys());
  }
}

// Singleton instance
export const toolRendererRegistry = new ToolRendererRegistry();
