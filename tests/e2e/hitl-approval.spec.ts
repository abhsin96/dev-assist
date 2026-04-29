/**
 * E2E Tests for HITL Approval UI (DEVHUB-023)
 *
 * Tests the complete approval workflow including:
 * - Approval card rendering
 * - Approve action
 * - Edit & Approve with argument modification
 * - Reject action
 * - Expiration handling
 * - Multiple pending approvals (FIFO)
 */

import { test, expect, Page } from "@playwright/test";

// Mock interrupt event data
const mockInterruptEvent = {
  approval_id: "approval-123",
  summary: "Delete production database 'users_prod'",
  risk: "critical",
  tool_name: "delete_database",
  tool_args: {
    database_name: "users_prod",
    confirm: true,
  },
  expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
};

const mockLowRiskInterruptEvent = {
  approval_id: "approval-456",
  summary: "Read configuration file",
  risk: "low",
  tool_name: "read_file",
  tool_args: {
    file_path: "/config/app.json",
  },
  expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
};

/**
 * Helper function to mock SSE stream with interrupt event
 */
async function mockInterruptStream(page: Page, interruptData: typeof mockInterruptEvent) {
  await page.route("**/api/runs/stream*", async (route) => {
    const stream = [
      `event: token\ndata: {"text":"I need your approval to proceed."}\n\n`,
      `event: interrupt\ndata: ${JSON.stringify(interruptData)}\n\n`,
      `event: done\ndata: {"run_id":"run-123"}\n\n`,
    ].join("");

    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: stream,
    });
  });
}

/**
 * Helper function to mock approval submission endpoint
 */
async function mockApprovalSubmission(page: Page, expectedDecision: "approved" | "rejected") {
  await page.route("**/api/runs/*/approvals", async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();

    expect(postData.decision).toBe(expectedDecision);

    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: "ok",
        decision: expectedDecision,
      }),
    });
  });
}

test.describe("HITL Approval UI", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user: { id: "user-123", email: "test@example.com" },
        }),
      });
    });

    // Mock thread data
    await page.route("**/api/threads/*", async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: "thread-123",
          title: "Test Thread",
          updatedAt: new Date().toISOString(),
          createdAt: new Date().toISOString(),
        }),
      });
    });

    // Mock run start endpoint
    await page.route("**/api/runs/start", async (route) => {
      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: "run-123" }),
      });
    });

    // Navigate to thread
    await page.goto("/threads/thread-123");
  });

  test("should render approval card inline when interrupt event is received", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);

    // Send a message to trigger the stream
    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card to appear
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Verify card content
    await expect(page.locator("text=Awaiting Approval")).toBeVisible();
    await expect(page.locator(`text=${mockInterruptEvent.summary}`)).toBeVisible();
    await expect(page.locator("text=Critical Risk")).toBeVisible();

    // Verify buttons are present
    await expect(page.locator('button:has-text("Approve")')).toBeVisible();
    await expect(page.locator('button:has-text("Edit & Approve")')).toBeVisible();
    await expect(page.locator('button:has-text("Reject")')).toBeVisible();
  });

  test("should display collapsible tool arguments", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Click to expand tool arguments
    await page.click('button:has-text("Tool Arguments")');

    // Verify arguments are displayed
    await expect(page.locator(`text=${mockInterruptEvent.tool_name}`)).toBeVisible();
    await expect(page.locator(`text=${mockInterruptEvent.tool_args.database_name}`)).toBeVisible();
  });

  test("should approve action and transition card to approved state", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);
    await mockApprovalSubmission(page, "approved");

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Click approve button
    await page.click('button:has-text("Approve")');

    // Verify card transitions to approved state
    await expect(page.locator("text=Approved")).toBeVisible();
    await expect(page.locator("text=This approval has been approved")).toBeVisible();

    // Verify action buttons are no longer visible
    await expect(page.locator('button:has-text("Approve")')).not.toBeVisible();
  });

  test("should allow editing arguments before approval", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Click "Edit & Approve" button
    await page.click('button:has-text("Edit & Approve")');

    // Verify editor appears
    await expect(page.locator('textarea[placeholder="Enter JSON arguments..."]')).toBeVisible();

    // Modify the arguments
    const modifiedArgs = {
      database_name: "users_dev", // Changed from users_prod
      confirm: true,
    };

    await page.fill(
      'textarea[placeholder="Enter JSON arguments..."]',
      JSON.stringify(modifiedArgs, null, 2)
    );

    // Mock approval with patched args
    await page.route("**/api/runs/*/approvals", async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      expect(postData.decision).toBe("approved");
      expect(postData.patched_args).toEqual(modifiedArgs);

      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "ok", decision: "approved" }),
      });
    });

    // Submit approval
    await page.click('button:has-text("Submit & Approve")');

    // Verify card transitions to approved state
    await expect(page.locator("text=Approved")).toBeVisible();
  });

  test("should reject action and transition card to rejected state", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);
    await mockApprovalSubmission(page, "rejected");

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Click reject button
    await page.click('button:has-text("Reject")');

    // Verify card transitions to rejected state
    await expect(page.locator("text=Rejected")).toBeVisible();
    await expect(page.locator("text=This approval has been rejected")).toBeVisible();
  });

  test("should display validation error for invalid JSON in editor", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Click "Edit & Approve" button
    await page.click('button:has-text("Edit & Approve")');

    // Enter invalid JSON
    await page.fill('textarea[placeholder="Enter JSON arguments..."]', "{ invalid json }");

    // Blur to trigger validation
    await page.locator('textarea[placeholder="Enter JSON arguments..."]').blur();

    // Verify error message
    await expect(page.locator("text=Invalid JSON format")).toBeVisible();

    // Verify submit button is disabled
    await expect(page.locator('button:has-text("Submit & Approve")')).toBeDisabled();
  });

  test("should handle multiple pending approvals in FIFO order", async ({ page }) => {
    // Mock stream with two interrupt events
    await page.route("**/api/runs/stream*", async (route) => {
      const stream = [
        `event: interrupt\ndata: ${JSON.stringify(mockInterruptEvent)}\n\n`,
        `event: interrupt\ndata: ${JSON.stringify(mockLowRiskInterruptEvent)}\n\n`,
        `event: done\ndata: {"run_id":"run-123"}\n\n`,
      ].join("");

      await route.fulfill({
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
        },
        body: stream,
      });
    });

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Verify both approval cards are visible
    const approvalCards = page.locator('[data-testid="hitl-approval-card"]');
    await expect(approvalCards).toHaveCount(2);

    // Verify FIFO order (critical risk should appear first based on expiration)
    const firstCard = approvalCards.first();
    const secondCard = approvalCards.last();

    await expect(firstCard.locator(`text=${mockInterruptEvent.summary}`)).toBeVisible();
    await expect(secondCard.locator(`text=${mockLowRiskInterruptEvent.summary}`)).toBeVisible();
  });

  test("should show expired state when approval expires", async ({ page }) => {
    // Create an approval that expires in 1 second
    const expiringSoonEvent = {
      ...mockInterruptEvent,
      expires_at: new Date(Date.now() + 1000).toISOString(),
    };

    await mockInterruptStream(page, expiringSoonEvent);

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Wait for expiration (polling interval is 5 seconds, but we can force it)
    await page.waitForTimeout(6000);

    // Verify expired state
    await expect(page.locator("text=Expired")).toBeVisible();
    await expect(page.locator('button:has-text("Retry Action")')).toBeVisible();

    // Verify action buttons are no longer visible
    await expect(page.locator('button:has-text("Approve")')).not.toBeVisible();
  });

  test("should display risk badges with correct colors", async ({ page }) => {
    await mockInterruptStream(page, mockInterruptEvent);

    await page.fill('textarea[placeholder="Type a message..."]', "Test message");
    await page.click('button[aria-label="Send"]');

    // Wait for approval card
    await expect(page.locator('[data-testid="hitl-approval-card"]')).toBeVisible();

    // Verify critical risk badge
    const riskBadge = page.locator('[data-testid="risk-badge"]');
    await expect(riskBadge).toHaveText("Critical Risk");
    await expect(riskBadge).toHaveClass(/bg-destructive/);
  });
});