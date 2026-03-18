import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const data = await request.json()

    const { workflowId, event, payload } = data

    if (!workflowId || !event) {
      return NextResponse.json({ error: "Missing workflow ID or event type" }, { status: 400 })
    }

    console.log("[v0] Automation webhook:", { workflowId, event })

    // Store event in database or trigger actions
    // Integration point: Update DuckDB/MySQL with event data

    return NextResponse.json({
      success: true,
      workflowId,
      processedAt: new Date().toISOString(),
    })
  } catch (error) {
    console.error("[v0] Automation webhook error:", error)
    return NextResponse.json({ error: "Failed to process automation" }, { status: 500 })
  }
}
