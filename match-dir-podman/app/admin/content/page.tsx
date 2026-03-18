"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { getContent, getCategories } from "@/lib/cms-service"
import { Plus, Edit2, Trash2 } from "lucide-react"

export default function ContentManagement() {
  const [content, setContent] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [contentData, categoriesData] = await Promise.all([getContent(), getCategories()])
        setContent(Array.isArray(contentData) ? contentData : [contentData])
        setCategories(categoriesData)
      } catch (error) {
        console.error("[v0] Failed to load content:", error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Content Management</h1>
          <p className="text-muted-foreground mt-1">Manage your CMS content powered by Directus</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          New Content
        </Button>
      </div>

      {/* Categories */}
      <Card>
        <CardHeader>
          <CardTitle>Content Categories</CardTitle>
          <CardDescription>Manage content organization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <Badge key={category.id} variant="outline" className="px-3 py-2">
                {category.name}
                <span className="ml-2 text-xs opacity-60">({category.itemCount})</span>
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Content List */}
      <Card>
        <CardHeader>
          <CardTitle>All Content</CardTitle>
          <CardDescription>Manage and organize your platform content</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-r-transparent mx-auto" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-medium">Title</th>
                    <th className="text-left py-3 px-4 font-medium">Category</th>
                    <th className="text-left py-3 px-4 font-medium">Status</th>
                    <th className="text-left py-3 px-4 font-medium">Updated</th>
                    <th className="text-left py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {content.map((item) => (
                    <tr key={item.id} className="border-b border-border hover:bg-card/50 transition">
                      <td className="py-3 px-4 font-medium">{item.title}</td>
                      <td className="py-3 px-4">
                        <Badge variant="outline">{item.category}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={item.status === "published" ? "default" : "outline"}>{item.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(item.updatedAt).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 space-x-2">
                        <Button variant="ghost" size="sm">
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
