import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  release: process.env.NEXT_PUBLIC_GIT_SHA,
  environment: process.env.NODE_ENV,

  // Capture 10% of transactions for performance monitoring
  tracesSampleRate: 0.1,

  // Attach the X-Request-Id from API responses as a custom tag so Sentry
  // events can be correlated with backend traces.
  beforeSend(event) {
    return event;
  },

  // Do not surface source maps in production bundles
  debug: false,
});
