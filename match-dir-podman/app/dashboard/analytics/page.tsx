"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Users, Target, Zap } from "lucide-react"

export default function AnalyticsPage() {
  const analytics = {
    totalMatches: 47,
    successRate: 92,
    avgCompatibility: 78,
    connectionsInitiated: 12,
    matchesByScore: [
      { range: "Excellent (80-100)", count: 15, color: "bg-green-100 text-green-800" },
      { range: "Good (60-79)", count: 22, color: "bg-yellow-100 text-yellow-800" },
      { range: "Fair (40-59)", count: 8, color: "bg-orange-100 text-orange-800" },
      { range: "Low (<40)", count: 2, color: "bg-red-100 text-red-800" },
    ],
    recentActivity: [
      { date: "2024-01-15", action: "Profile Updated", type: "update" },
      { date: "2024-01-12", action: "New Match Found", type: "match" },
      { date: "2024-01-10", action: "Connection Initiated", type: "connection" },
      { date: "2024-01-08", action: "Document Uploaded", type: "upload" },
    ],
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Analytics</h1>
        <p className="text-muted-foreground mt-1">Track your matching performance and activity</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Matches</p>
                <p className="text-2xl font-bold mt-1">{analytics.totalMatches}</p>
              </div>
              <Users className="w-8 h-8 text-primary opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Success Rate</p>
                <p className="text-2xl font-bold mt-1">{analytics.successRate}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Compatibility</p>
                <p className="text-2xl font-bold mt-1">{analytics.avgCompatibility}%</p>
              </div>
              <Target className="w-8 h-8 text-blue-600 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Connections</p>
                <p className="text-2xl font-bold mt-1">{analytics.connectionsInitiated}</p>
              </div>
              <Zap className="w-8 h-8 text-yellow-600 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Match Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Match Distribution</CardTitle>
          <CardDescription>Breakdown of matches by compatibility score</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {analytics.matchesByScore.map((item) => (
            <div key={item.range}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{item.range}</span>
                <Badge className={item.color}>{item.count}</Badge>
              </div>
              <div className="w-full bg-border rounded h-2 overflow-hidden">
                <div
                  className="bg-primary h-full"
                  style={{
                    width: `${(item.count / analytics.totalMatches) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your latest actions on the platform</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {analytics.recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between pb-3 border-b border-border last:border-0">
                <div>
                  <p className="text-sm font-medium">{activity.action}</p>
                  <p className="text-xs text-muted-foreground">{activity.date}</p>
                </div>
                <Badge variant="outline">{activity.type}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
