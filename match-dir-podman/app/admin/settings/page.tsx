"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

export default function AdminSettings() {
  const [settings, setSettings] = useState({
    platformName: "Matchgorithm",
    maxFileSize: 10,
    documentTimeout: 300,
    matchingThreshold: 70,
    maintenanceMode: false,
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Platform configuration and administration</p>
      </div>

      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>Platform configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Platform Name</label>
            <Input
              value={settings.platformName}
              onChange={(e) => setSettings({ ...settings, platformName: e.target.value })}
              className="mt-2"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Max File Size (MB)</label>
            <Input
              type="number"
              value={settings.maxFileSize}
              onChange={(e) => setSettings({ ...settings, maxFileSize: Number.parseInt(e.target.value) })}
              className="mt-2"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Document Processing Timeout (s)</label>
            <Input
              type="number"
              value={settings.documentTimeout}
              onChange={(e) => setSettings({ ...settings, documentTimeout: Number.parseInt(e.target.value) })}
              className="mt-2"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Matching Score Threshold (%)</label>
            <Input
              type="number"
              value={settings.matchingThreshold}
              onChange={(e) => setSettings({ ...settings, matchingThreshold: Number.parseInt(e.target.value) })}
              className="mt-2"
            />
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
          <CardDescription>Platform health and maintenance</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-border rounded">
            <div>
              <p className="font-medium">Maintenance Mode</p>
              <p className="text-sm text-muted-foreground">Take platform offline for maintenance</p>
            </div>
            <input
              type="checkbox"
              checked={settings.maintenanceMode}
              onChange={(e) => setSettings({ ...settings, maintenanceMode: e.target.checked })}
              className="w-6 h-6"
            />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 border border-border rounded">
              <p className="text-sm font-medium mb-2">Last Backup</p>
              <p className="text-sm text-muted-foreground">2024-01-15 03:45 UTC</p>
              <Button size="sm" variant="outline" className="mt-3 w-full bg-transparent">
                Backup Now
              </Button>
            </div>
            <div className="p-4 border border-border rounded">
              <p className="text-sm font-medium mb-2">Database Size</p>
              <p className="text-sm text-muted-foreground">2.4 GB</p>
              <Button size="sm" variant="outline" className="mt-3 w-full bg-transparent">
                Optimize
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end gap-2">
        <Button variant="outline">Cancel</Button>
        <Button>Save Settings</Button>
      </div>
    </div>
  )
}
