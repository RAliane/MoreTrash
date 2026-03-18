// Client-side automation service

interface WorkflowTriggerRequest {
  workflowId: string
  event: string
  data: Record<string, any>
}

interface Campaign {
  id: string
  name: string
  type: "welcome" | "digest" | "notification" | "promotional"
  status: "draft" | "scheduled" | "running" | "completed"
  recipients: number
  sentAt?: string
  openRate?: number
  clickRate?: number
}

interface Automation {
  id: string
  name: string
  trigger: string
  action: string
  enabled: boolean
  executionCount: number
  lastRun?: string
}

export async function triggerWorkflow(request: WorkflowTriggerRequest) {
  const response = await fetch("/api/workflows/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error("Failed to trigger workflow")
  }

  return response.json()
}

export async function getCampaigns(): Promise<Campaign[]> {
  const response = await fetch("/api/workflows/campaigns")

  if (!response.ok) {
    throw new Error("Failed to fetch campaigns")
  }

  return response.json()
}

export async function createCampaign(campaign: Omit<Campaign, "id">): Promise<Campaign> {
  const response = await fetch("/api/workflows/campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(campaign),
  })

  if (!response.ok) {
    throw new Error("Failed to create campaign")
  }

  return response.json()
}

export async function getAutomations(): Promise<Automation[]> {
  const response = await fetch("/api/workflows/automations")

  if (!response.ok) {
    throw new Error("Failed to fetch automations")
  }

  return response.json()
}

export async function updateAutomation(id: string, enabled: boolean): Promise<Automation> {
  const response = await fetch("/api/workflows/automations", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, enabled }),
  })

  if (!response.ok) {
    throw new Error("Failed to update automation")
  }

  return response.json()
}
