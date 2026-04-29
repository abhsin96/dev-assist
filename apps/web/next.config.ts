import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React Compiler for better performance
  reactCompiler: true,
};

export default withSentryConfig(nextConfig, {
  // Sentry org/project slugs (set these in CI env vars)
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Suppress upload warnings when SENTRY_AUTH_TOKEN is not set (local dev)
  silent: !process.env.CI,

  // Upload source maps to Sentry during build
  widenClientFileUpload: true,

  // Automatically tree-shake Sentry logger statements in production
  disableLogger: true,
});
