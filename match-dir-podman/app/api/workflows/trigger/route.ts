import { type NextRequest, NextResponse } from "next/server"

interface WorkflowTrigger {
  workflowId: string
  event: string
  data: Record<string, any>
}

interface WorkflowResponse {
  executionId: string
  status: "queued" | "running" | "completed" | "failed"
  workflowId: string
  triggeredAt: string
}

// Placeholder n8n webhook management
const activeWorkflows = new Map<string, any>()

export async function POST(request: NextRequest) {
  try {
    const body: WorkflowTrigger = await request.json()
    const { workflowId, event, data } = body

    if (!workflowId || !event) {
      return NextResponse.json({ error: "workflowId and event are required" }, { status: 400 })
    }

    console.log("[v0] Workflow triggered:", { workflowId, event, dataKeys: Object.keys(data) })

    // In production, this would call n8n webhook API
    // Example: POST to https://your-n8n-instance.com/webhook/{workflowId}

    const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const response: WorkflowResponse = {
      executionId,
      status: "queued",
      workflowId,
      triggeredAt: new Date().toISOString(),
    }

    activeWorkflows.set(executionId, response)

    return NextResponse.json(response, { status: 202 })
  } catch (error) {
    console.error("[v0] Workflow trigger error:", error)
    return NextResponse.json({ error: "Failed to trigger workflow" }, { status: 500 })
  }
}
