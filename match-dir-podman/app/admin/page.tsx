"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Users, TrendingUp, Activity, Zap } from "lucide-react"

export default function AdminDashboard() {
  const stats = [
    {
      title: "Total Users",
      value: "1,247",
      change: "+12%",
      icon: Users,
      color: "text-blue-600",
    },
    {
      title: "Active Matches",
      value: "3,891",
      change: "+24%",
      icon: TrendingUp,
      color: "text-green-600",
    },
    {
      title: "System Health",
      value: "99.8%",
      change: "Stable",
      icon: Activity,
      color: "text-yellow-600",
    },
    {
      title: "API Requests",
      value: "245K",
      change: "+8%",
      icon: Zap,
      color: "text-purple-600",
    },
  ]

  const recentUsers = [
    { id: 1, name: "Sarah Johnson", email: "sarah@example.com", joined: "2024-01-15", status: "active" },
    { id: 2, name: "Mike Chen", email: "mike@example.com", joined: "2024-01-14", status: "active" },
    { id: 3, name: "Emily Rodriguez", email: "emily@example.com", joined: "2024-01-13", status: "inactive" },
    { id: 4, name: "James Wilson", email: "james@example.com", joined: "2024-01-12", status: "active" },
    { id: 5, name: "Lisa Anderson", email: "lisa@example.com", joined: "2024-01-11", status: "active" },
  ]

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-1">Platform overview and key metrics</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.title}</p>
                  <p className="text-2xl font-bold mt-2">{stat.value}</p>
                  <p className="text-xs text-green-600 mt-2">{stat.change}</p>
                </div>
                <stat.icon className={`w-8 h-8 ${stat.color} opacity-20`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System Status */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>Current platform performance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { name: "Database", status: "healthy", latency: "2ms" },
              { name: "API Gateway", status: "healthy", latency: "5ms" },
              { name: "Document Parser", status: "healthy", latency: "150ms" },
              { name: "Matcher Engine", status: "healthy", latency: "245ms" },
            ].map((service) => (
              <div
                key={service.name}
                className="flex items-center justify-between pb-3 border-b border-border last:border-0"
              >
                <div>
                  <p className="text-sm font-medium">{service.name}</p>
                  <p className="text-xs text-muted-foreground">Response: {service.latency}</p>
                </div>
                <Badge className="bg-green-100 text-green-800">Online</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Platform Statistics</CardTitle>
            <CardDescription>Last 30 days summary</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "New Users", value: "284" },
              { label: "Matches Generated", value: "12,847" },
              { label: "Documents Processed", value: "4,521" },
              { label: "API Errors", value: "12" },
            ].map((stat) => (
              <div key={stat.label} className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="text-sm font-bold">{stat.value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Users */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Users</CardTitle>
          <CardDescription>Latest signups and activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 font-medium">Name</th>
                  <th className="text-left py-3 px-2 font-medium">Email</th>
                  <th className="text-left py-3 px-2 font-medium">Joined</th>
                  <th className="text-left py-3 px-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentUsers.map((user) => (
                  <tr key={user.id} className="border-b border-border hover:bg-card/50 transition">
                    <td className="py-3 px-2 font-medium">{user.name}</td>
                    <td className="py-3 px-2 text-muted-foreground">{user.email}</td>
                    <td className="py-3 px-2 text-muted-foreground">{user.joined}</td>
                    <td className="py-3 px-2">
                      <Badge variant={user.status === "active" ? "default" : "outline"}>{user.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
