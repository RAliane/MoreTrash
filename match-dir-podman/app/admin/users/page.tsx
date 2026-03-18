"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, MoreVertical } from "lucide-react"

export default function UsersManagement() {
  const [searchTerm, setSearchTerm] = useState("")
  const [filter, setFilter] = useState("all")

  const users = [
    {
      id: 1,
      name: "Sarah Johnson",
      email: "sarah@example.com",
      role: "user",
      status: "active",
      joined: "2024-01-15",
      matches: 12,
    },
    {
      id: 2,
      name: "Mike Chen",
      email: "mike@example.com",
      role: "user",
      status: "active",
      joined: "2024-01-14",
      matches: 8,
    },
    {
      id: 3,
      name: "Emily Rodriguez",
      email: "emily@example.com",
      role: "admin",
      status: "active",
      joined: "2024-01-01",
      matches: 25,
    },
    {
      id: 4,
      name: "James Wilson",
      email: "james@example.com",
      role: "user",
      status: "inactive",
      joined: "2024-01-12",
      matches: 0,
    },
    {
      id: 5,
      name: "Lisa Anderson",
      email: "lisa@example.com",
      role: "user",
      status: "active",
      joined: "2024-01-11",
      matches: 15,
    },
  ]

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filter === "all" || user.status === filter
    return matchesSearch && matchesFilter
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">User Management</h1>
        <p className="text-muted-foreground mt-1">Manage platform users and permissions</p>
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              {["all", "active", "inactive"].map((status) => (
                <Button
                  key={status}
                  variant={filter === status ? "default" : "outline"}
                  onClick={() => setFilter(status)}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
          <CardDescription>Total: {filteredUsers.length} users</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-medium">Name</th>
                  <th className="text-left py-3 px-4 font-medium">Email</th>
                  <th className="text-left py-3 px-4 font-medium">Role</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Matches</th>
                  <th className="text-left py-3 px-4 font-medium">Joined</th>
                  <th className="text-left py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="border-b border-border hover:bg-card/50 transition">
                    <td className="py-3 px-4 font-medium">{user.name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{user.email}</td>
                    <td className="py-3 px-4">
                      <Badge variant="outline">{user.role}</Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={user.status === "active" ? "default" : "outline"}>{user.status}</Badge>
                    </td>
                    <td className="py-3 px-4">{user.matches}</td>
                    <td className="py-3 px-4 text-muted-foreground">{user.joined}</td>
                    <td className="py-3 px-4">
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
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
