import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  release: process.env.GIT_SHA,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  debug: false,
});
