import { type NextRequest, NextResponse } from "next/server"

interface EmailCampaign {
  id: string
  name: string
  type: "welcome" | "digest" | "notification" | "promotional"
  status: "draft" | "scheduled" | "running" | "completed"
  recipients: number
  sentAt?: string
  openRate?: number
  clickRate?: number
}

const campaigns: EmailCampaign[] = [
  {
    id: "camp_001",
    name: "Welcome New Users",
    type: "welcome",
    status: "running",
    recipients: 145,
    openRate: 68,
    clickRate: 32,
  },
  {
    id: "camp_002",
    name: "Weekly Matches Digest",
    type: "digest",
    status: "scheduled",
    recipients: 0,
  },
  {
    id: "camp_003",
    name: "Match Notifications",
    type: "notification",
    status: "running",
    recipients: 892,
    openRate: 85,
    clickRate: 42,
  },
]

export async function GET() {
  try {
    return NextResponse.json(campaigns)
  } catch (error) {
    console.error("[v0] Campaigns fetch error:", error)
    return NextResponse.json({ error: "Failed to fetch campaigns" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: Omit<EmailCampaign, "id"> = await request.json()

    const newCampaign: EmailCampaign = {
      id: `camp_${Date.now()}`,
      ...body,
    }

    campaigns.push(newCampaign)
    return NextResponse.json(newCampaign, { status: 201 })
  } catch (error) {
    console.error("[v0] Campaign creation error:", error)
    return NextResponse.json({ error: "Failed to create campaign" }, { status: 500 })
  }
}
