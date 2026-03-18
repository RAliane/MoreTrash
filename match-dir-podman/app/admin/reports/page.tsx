"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { exportAnalytics } from "@/lib/cms-service"
import { Download, Calendar } from "lucide-react"

export default function ReportsPage() {
  const [startDate, setStartDate] = useState("2024-01-01")
  const [endDate, setEndDate] = useState("2024-01-31")
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: "csv" | "json") => {
    setExporting(true)
    try {
      const blob = await exportAnalytics(format, startDate, endDate)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `analytics_${startDate}_to_${endDate}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("[v0] Export failed:", error)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Reports & Analytics</h1>
        <p className="text-muted-foreground mt-1">Export and analyze platform data with DuckDB</p>
      </div>

      {/* Export Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Export Data</CardTitle>
          <CardDescription>Download analytics and platform data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Start Date</label>
              <div className="flex gap-2 mt-2">
                <Calendar className="w-4 h-4 text-muted-foreground mt-3" />
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">End Date</label>
              <div className="flex gap-2 mt-2">
                <Calendar className="w-4 h-4 text-muted-foreground mt-3" />
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={() => handleExport("csv")} disabled={exporting} className="gap-2">
              <Download className="w-4 h-4" />
              Export CSV
            </Button>
            <Button onClick={() => handleExport("json")} disabled={exporting} variant="outline" className="gap-2">
              <Download className="w-4 h-4" />
              Export JSON
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Available Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Available Reports</CardTitle>
          <CardDescription>Pre-built reports powered by DuckDB</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { name: "User Growth Report", description: "Daily user registration and activity trends" },
              { name: "Matching Performance", description: "Match quality, success rates, and processing times" },
              { name: "Document Processing", description: "Document upload volume and processing metrics" },
              { name: "Platform Metrics", description: "System performance, uptime, and API usage" },
            ].map((report) => (
              <div
                key={report.name}
                className="flex items-center justify-between p-4 border border-border rounded hover:bg-card/50 transition"
              >
                <div>
                  <p className="font-medium">{report.name}</p>
                  <p className="text-sm text-muted-foreground">{report.description}</p>
                </div>
                <Button size="sm" variant="outline">
                  View
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
