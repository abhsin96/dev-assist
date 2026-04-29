/**
 * Register all tool renderers
 */

import { toolRendererRegistry } from "./tool-renderer-registry";
import {
  PRDiffCard,
  IssueCard,
  CodeSearchResult,
  DocDiffCard,
} from "@/components/tools";

/**
 * Register all available tool renderers
 * This should be called once during app initialization
 */
export function registerToolRenderers(): void {
  // GitHub-related tools
  toolRendererRegistry.register("github_get_pr_diff", PRDiffCard);
  toolRendererRegistry.register("github_fetch_pr", PRDiffCard);
  toolRendererRegistry.register("get_pr_diff", PRDiffCard);
  
  toolRendererRegistry.register("github_get_issue", IssueCard);
  toolRendererRegistry.register("github_fetch_issue", IssueCard);
  toolRendererRegistry.register("get_issue", IssueCard);
  
  // Code search tools
  toolRendererRegistry.register("code_search", CodeSearchResult);
  toolRendererRegistry.register("search_code", CodeSearchResult);
  toolRendererRegistry.register("grep_code", CodeSearchResult);
  
  // Documentation tools
  toolRendererRegistry.register("doc_diff", DocDiffCard);
  toolRendererRegistry.register("get_doc_diff", DocDiffCard);
  toolRendererRegistry.register("compare_docs", DocDiffCard);
}
