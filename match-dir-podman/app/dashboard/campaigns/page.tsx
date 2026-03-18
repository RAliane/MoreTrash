"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { TrendingUp, Users, DollarSign, MousePointerClick } from "lucide-react"

const chartData = [
  { name: "Jan", leads: 400, clicks: 2400, conversions: 240 },
  { name: "Feb", leads: 600, clicks: 2210, conversions: 221 },
  { name: "Mar", leads: 800, clicks: 2290, conversions: 229 },
  { name: "Apr", leads: 1200, clicks: 2000, conversions: 200 },
  { name: "May", leads: 1400, clicks: 2181, conversions: 500 },
  { name: "Jun", leads: 1800, clicks: 2500, conversions: 800 },
]

export default function CampaignsPage() {
  const [campaigns] = useState([
    { id: 1, name: "Summer Campaign", status: "active", leads: 1234, spent: "$450", roi: "320%" },
    { id: 2, name: "Q2 Lead Gen", status: "paused", leads: 856, spent: "$320", roi: "245%" },
    { id: 3, name: "Affiliate Push", status: "active", leads: 2341, spent: "$890", roi: "415%" },
  ])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Campaigns</h1>
          <p className="text-muted-foreground">Monitor and manage your marketing campaigns</p>
        </div>
        <Button>Create Campaign</Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { icon: Users, label: "Total Leads", value: "4,431", change: "+12.5%" },
          { icon: DollarSign, label: "Revenue", value: "$12,450", change: "+18.2%" },
          { icon: MousePointerClick, label: "Clicks", value: "24,891", change: "+5.3%" },
          { icon: TrendingUp, label: "Avg ROI", value: "327%", change: "+22%" },
        ].map((stat) => (
          <Card key={stat.label} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="text-2xl font-bold text-foreground mt-2">{stat.value}</p>
                <p className="text-xs text-green-500 mt-2">{stat.change}</p>
              </div>
              <stat.icon className="w-8 h-8 text-primary opacity-20" />
            </div>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Leads Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis stroke="var(--muted-foreground)" />
              <YAxis stroke="var(--muted-foreground)" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="leads" stroke="var(--primary)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Conversions by Campaign</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis stroke="var(--muted-foreground)" />
              <YAxis stroke="var(--muted-foreground)" />
              <Tooltip />
              <Legend />
              <Bar dataKey="conversions" fill="var(--primary)" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Campaigns Table */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">Active Campaigns</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border">
              <tr>
                <th className="text-left py-3 px-4 font-semibold text-foreground">Campaign</th>
                <th className="text-left py-3 px-4 font-semibold text-foreground">Status</th>
                <th className="text-left py-3 px-4 font-semibold text-foreground">Leads</th>
                <th className="text-left py-3 px-4 font-semibold text-foreground">Spent</th>
                <th className="text-left py-3 px-4 font-semibold text-foreground">ROI</th>
                <th className="text-left py-3 px-4 font-semibold text-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr key={campaign.id} className="border-b border-border hover:bg-muted/50">
                  <td className="py-3 px-4 text-foreground">{campaign.name}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        campaign.status === "active"
                          ? "bg-green-500/20 text-green-500"
                          : "bg-yellow-500/20 text-yellow-500"
                      }`}
                    >
                      {campaign.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-foreground">{campaign.leads}</td>
                  <td className="py-3 px-4 text-foreground">{campaign.spent}</td>
                  <td className="py-3 px-4 text-green-500 font-semibold">{campaign.roi}</td>
                  <td className="py-3 px-4">
                    <Button variant="ghost" size="sm">
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
