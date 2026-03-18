import { type NextRequest, NextResponse } from "next/server"

interface Automation {
  id: string
  name: string
  trigger: string
  action: string
  enabled: boolean
  executionCount: number
  lastRun?: string
}

const automations: Automation[] = [
  {
    id: "auto_001",
    name: "Send match notification",
    trigger: "New match found",
    action: "Send email notification",
    enabled: true,
    executionCount: 1247,
    lastRun: "2024-01-15T14:30:00Z",
  },
  {
    id: "auto_002",
    name: "Weekly digest email",
    trigger: "Every Monday 9:00 AM",
    action: "Send digest with top 5 matches",
    enabled: true,
    executionCount: 52,
    lastRun: "2024-01-15T09:00:00Z",
  },
  {
    id: "auto_003",
    name: "Inactive user reminder",
    trigger: "User inactive for 30 days",
    action: "Send re-engagement email",
    enabled: true,
    executionCount: 284,
    lastRun: "2024-01-14T20:15:00Z",
  },
  {
    id: "auto_004",
    name: "Profile completion reminder",
    trigger: "Profile less than 50% complete",
    action: "Send completion prompt",
    enabled: false,
    executionCount: 156,
  },
]

export async function GET() {
  try {
    return NextResponse.json(automations)
  } catch (error) {
    console.error("[v0] Automations fetch error:", error)
    return NextResponse.json({ error: "Failed to fetch automations" }, { status: 500 })
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const body: { id: string; enabled: boolean } = await request.json()

    const automation = automations.find((a) => a.id === body.id)
    if (!automation) {
      return NextResponse.json({ error: "Automation not found" }, { status: 404 })
    }

    automation.enabled = body.enabled
    return NextResponse.json(automation)
  } catch (error) {
    console.error("[v0] Automation update error:", error)
    return NextResponse.json({ error: "Failed to update automation" }, { status: 500 })
  }
}
