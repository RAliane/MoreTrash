"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export default function AnalyticsPage() {
  const metrics = [
    {
      category: "User Growth",
      data: [
        { label: "New Users (7d)", value: 47 },
        { label: "New Users (30d)", value: 284 },
        { label: "Total Users", value: "1,247" },
        { label: "Active Users", value: "891" },
      ],
    },
    {
      category: "Matching Performance",
      data: [
        { label: "Matches Generated", value: "12,847" },
        { label: "Avg Quality Score", value: "78%" },
        { label: "Success Rate", value: "92%" },
        { label: "Processing Time", value: "245ms" },
      ],
    },
    {
      category: "Document Processing",
      data: [
        { label: "Documents Processed", value: "4,521" },
        { label: "Avg Processing Time", value: "2.3s" },
        { label: "Success Rate", value: "99.2%" },
        { label: "Formats Supported", value: "5" },
      ],
    },
    {
      category: "System Performance",
      data: [
        { label: "API Uptime", value: "99.99%" },
        { label: "Avg Response Time", value: "145ms" },
        { label: "Error Rate", value: "0.02%" },
        { label: "Total API Calls", value: "245K" },
      ],
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Platform Analytics</h1>
        <p className="text-muted-foreground mt-1">Comprehensive platform metrics and performance data</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {metrics.map((section) => (
          <Card key={section.category}>
            <CardHeader>
              <CardTitle className="text-lg">{section.category}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {section.data.map((metric) => (
                <div
                  key={metric.label}
                  className="flex items-center justify-between pb-3 border-b border-border last:border-0"
                >
                  <p className="text-sm text-muted-foreground">{metric.label}</p>
                  <p className="text-sm font-bold">{metric.value}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Top Performing Features */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Usage</CardTitle>
          <CardDescription>Most used features in the platform</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { name: "Document Upload", usage: "89%", color: "bg-blue-100 text-blue-800" },
              { name: "Match Analysis", usage: "85%", color: "bg-green-100 text-green-800" },
              { name: "Profile Viewing", usage: "76%", color: "bg-yellow-100 text-yellow-800" },
              { name: "Connection Messaging", usage: "62%", color: "bg-purple-100 text-purple-800" },
            ].map((feature) => (
              <div key={feature.name} className="flex items-center justify-between">
                <p className="text-sm font-medium">{feature.name}</p>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-border rounded">
                    <div className="h-full bg-primary rounded" style={{ width: feature.usage }} />
                  </div>
                  <Badge className={feature.color}>{feature.usage}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
