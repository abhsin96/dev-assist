import { NextRequest, NextResponse } from "next/server";
import type { TraceData, TraceStep } from "@/components/trace";

/**
 * GET /api/runs/[runId]/trace
 * Fetches the complete trace data for a specific run
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;

    if (!runId) {
      return NextResponse.json(
        { error: "Run ID is required" },
        { status: 400 },
      );
    }

    // TODO: Replace with actual backend API call
    // For now, return mock data for development
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/runs/${runId}/trace`, {
      headers: {
        "Content-Type": "application/json",
        // Add auth headers if needed
        // Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      // If backend doesn't have trace endpoint yet, return mock data
      if (response.status === 404) {
        return NextResponse.json(createMockTraceData(runId));
      }

      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching trace data:", error);

    // Return mock data for development
    const { runId } = await params;
    return NextResponse.json(createMockTraceData(runId));
  }
}

/**
 * Creates mock trace data for development/testing
 */
function createMockTraceData(runId: string): TraceData {
  const steps: TraceStep[] = [
    {
      id: "step_1",
      agentName: "Router",
      description: "Analyzing user request and routing to appropriate agent",
      status: "success",
      duration: 145,
      startTime: new Date(Date.now() - 5000).toISOString(),
      endTime: new Date(Date.now() - 4855).toISOString(),
      metadata: {
        decision: "route_to_code_agent",
        confidence: 0.95,
      },
      children: [
        {
          id: "step_1_1",
          agentName: "Router",
          toolName: "analyze_intent",
          description: "Analyzing user intent",
          args: {
            query: "Fix the login bug",
          },
          result: {
            intent: "code_modification",
            confidence: 0.95,
          },
          status: "success",
          duration: 89,
          startTime: new Date(Date.now() - 4950).toISOString(),
          endTime: new Date(Date.now() - 4861).toISOString(),
        },
      ],
    },
    {
      id: "step_2",
      agentName: "CodeAgent",
      description: "Searching for relevant code files",
      status: "success",
      duration: 523,
      startTime: new Date(Date.now() - 4800).toISOString(),
      endTime: new Date(Date.now() - 4277).toISOString(),
      children: [
        {
          id: "step_2_1",
          agentName: "CodeAgent",
          toolName: "search_code",
          description: "Searching codebase for login functionality",
          args: {
            query: "login authentication",
            file_pattern: "*.ts",
          },
          result: {
            files: [
              "src/auth/login.ts",
              "src/components/LoginForm.tsx",
            ],
            matches: 12,
          },
          status: "success",
          duration: 423,
          startTime: new Date(Date.now() - 4750).toISOString(),
          endTime: new Date(Date.now() - 4327).toISOString(),
        },
        {
          id: "step_2_2",
          agentName: "CodeAgent",
          toolName: "read_file",
          description: "Reading login.ts file",
          args: {
            path: "src/auth/login.ts",
          },
          result: {
            content: "// Login implementation...",
            lines: 145,
          },
          status: "success",
          duration: 100,
          startTime: new Date(Date.now() - 4300).toISOString(),
          endTime: new Date(Date.now() - 4200).toISOString(),
        },
      ],
    },
    {
      id: "step_3",
      agentName: "CodeAgent",
      description: "Analyzing code and identifying bug",
      status: "success",
      duration: 1234,
      startTime: new Date(Date.now() - 4200).toISOString(),
      endTime: new Date(Date.now() - 2966).toISOString(),
      metadata: {
        bug_found: true,
        location: "line 42",
      },
    },
    {
      id: "step_4",
      agentName: "CodeAgent",
      toolName: "edit_file",
      description: "Applying fix to login.ts",
      args: {
        path: "src/auth/login.ts",
        changes: [
          {
            line: 42,
            old: "if (user.password = hashedPassword)",
            new: "if (user.password === hashedPassword)",
          },
        ],
      },
      result: {
        success: true,
        lines_changed: 1,
      },
      status: "success",
      duration: 234,
      startTime: new Date(Date.now() - 2900).toISOString(),
      endTime: new Date(Date.now() - 2666).toISOString(),
    },
    {
      id: "step_5",
      agentName: "TestAgent",
      description: "Running tests to verify fix",
      status: "success",
      duration: 2156,
      startTime: new Date(Date.now() - 2600).toISOString(),
      endTime: new Date(Date.now() - 444).toISOString(),
      children: [
        {
          id: "step_5_1",
          agentName: "TestAgent",
          toolName: "run_tests",
          description: "Running authentication tests",
          args: {
            test_pattern: "auth/**/*.test.ts",
          },
          result: {
            passed: 24,
            failed: 0,
            duration: 2100,
          },
          status: "success",
          duration: 2100,
          startTime: new Date(Date.now() - 2550).toISOString(),
          endTime: new Date(Date.now() - 450).toISOString(),
        },
      ],
    },
  ];

  return {
    runId,
    steps,
    totalDuration: steps.reduce((sum, step) => sum + (step.duration || 0), 0),
    status: "completed",
  };
}
