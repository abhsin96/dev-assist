// Jest setup file for additional configuration
// Add custom matchers, global mocks, etc.

// Polyfill fetch and Response for Node.js test environment
import { TextEncoder, TextDecoder } from "util";
import { Blob } from "buffer";

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.Blob = Blob;

// Polyfill Response for tests
if (typeof global.Response === "undefined") {
  global.Response = class Response {
    constructor(body, init = {}) {
      this._body = body;
      this.status = init.status || 200;
      this.statusText = init.statusText || "OK";
      this._headers = new Map(Object.entries(init.headers || {}));
      this.ok = this.status >= 200 && this.status < 300;

      // Create headers object with get method
      this.headers = {
        get: (name) => {
          return this._headers.get(name.toLowerCase()) || null;
        },
      };
    }

    async json() {
      return JSON.parse(this._body);
    }

    async text() {
      return this._body;
    }
  };
}

// Mock Next.js router
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock window.matchMedia for theme detection
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(() => Promise.resolve()),
    readText: jest.fn(() => Promise.resolve("")),
  },
});
