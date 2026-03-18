"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { getAutomations, updateAutomation, getCampaigns } from "@/lib/automation-service"
import { Mail, Zap, Send, Clock } from "lucide-react"

export default function AutomationPage() {
  const [automations, setAutomations] = useState<any[]>([])
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [autoData, campData] = await Promise.all([getAutomations(), getCampaigns()])
        setAutomations(autoData)
        setCampaigns(campData)
      } catch (error) {
        console.error("[v0] Failed to load automation data:", error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  const handleToggleAutomation = async (id: string, enabled: boolean) => {
    try {
      const updated = await updateAutomation(id, !enabled)
      setAutomations(automations.map((a) => (a.id === id ? updated : a)))
    } catch (error) {
      console.error("[v0] Failed to update automation:", error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Marketing Automation</h1>
        <p className="text-muted-foreground mt-1">Manage n8n workflows and email campaigns</p>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Automations</p>
                <p className="text-2xl font-bold mt-1">{automations.filter((a) => a.enabled).length}</p>
              </div>
              <Zap className="w-8 h-8 text-yellow-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Campaigns</p>
                <p className="text-2xl font-bold mt-1">{campaigns.filter((c) => c.status === "running").length}</p>
              </div>
              <Mail className="w-8 h-8 text-blue-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Executions</p>
                <p className="text-2xl font-bold mt-1">{automations.reduce((sum, a) => sum + a.executionCount, 0)}</p>
              </div>
              <Clock className="w-8 h-8 text-green-600 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Automations */}
      <Card>
        <CardHeader>
          <CardTitle>Active Automations</CardTitle>
          <CardDescription>Manage your n8n workflows</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-r-transparent mx-auto" />
            </div>
          ) : (
            <div className="space-y-3">
              {automations.map((automation) => (
                <div
                  key={automation.id}
                  className="flex items-center justify-between p-4 border border-border rounded hover:bg-card/50 transition"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold">{automation.name}</h3>
                      <Badge variant={automation.enabled ? "default" : "outline"}>
                        {automation.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Trigger: {automation.trigger}</p>
                    <p className="text-sm text-muted-foreground">Action: {automation.action}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Executions: {automation.executionCount} | Last run:{" "}
                      {automation.lastRun ? new Date(automation.lastRun).toLocaleDateString() : "Never"}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant={automation.enabled ? "default" : "outline"}
                    onClick={() => handleToggleAutomation(automation.id, automation.enabled)}
                  >
                    {automation.enabled ? "Disable" : "Enable"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Email Campaigns */}
      <Card>
        <CardHeader>
          <CardTitle>Email Campaigns</CardTitle>
          <CardDescription>Manage marketing campaigns</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-4 border border-border rounded">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{campaign.name}</h3>
                    <Badge variant="outline">{campaign.type}</Badge>
                    <Badge variant={campaign.status === "running" ? "default" : "outline"}>{campaign.status}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Recipients: {campaign.recipients}
                    {campaign.openRate && ` | Open Rate: ${campaign.openRate}%`}
                    {campaign.clickRate && ` | Click Rate: ${campaign.clickRate}%`}
                  </p>
                </div>
                <Button size="sm" variant="outline" className="gap-2 bg-transparent">
                  <Send className="w-4 h-4" />
                  View
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* n8n Integration Info */}
      <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/20">
        <CardHeader>
          <CardTitle className="text-blue-900 dark:text-blue-100">n8n Integration</CardTitle>
          <CardDescription className="text-blue-800 dark:text-blue-200">
            Your automation workflows are powered by n8n
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-blue-800 dark:text-blue-200">
          <p className="mb-2">
            All workflows are connected to your n8n instance. Configure webhooks, email providers, and custom logic in
            n8n dashboard.
          </p>
          <Button className="gap-2 bg-transparent" variant="outline" size="sm">
            <Zap className="w-4 h-4" />
            Open n8n Dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
