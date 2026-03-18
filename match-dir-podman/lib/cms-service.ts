// Client-side CMS service

interface ContentItem {
  id: string
  title: string
  slug: string
  content: string
  status: "published" | "draft"
  category: string
  createdAt: string
  updatedAt: string
}

interface Category {
  id: string
  name: string
  slug: string
  description: string
  itemCount: number
}

export async function getContent(params?: {
  id?: string
  slug?: string
  category?: string
}): Promise<ContentItem | ContentItem[]> {
  const queryParams = new URLSearchParams()

  if (params?.id) queryParams.append("id", params.id)
  if (params?.slug) queryParams.append("slug", params.slug)
  if (params?.category) queryParams.append("category", params.category)

  const response = await fetch(`/api/cms/content?${queryParams}`)

  if (!response.ok) {
    throw new Error("Failed to fetch content")
  }

  return response.json()
}

export async function getCategories(): Promise<Category[]> {
  const response = await fetch("/api/cms/categories")

  if (!response.ok) {
    throw new Error("Failed to fetch categories")
  }

  return response.json()
}

export async function queryAnalytics(metric: string, timeRange: "7d" | "30d" | "90d" = "30d") {
  const response = await fetch("/api/analytics/duckdb", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ metric, timeRange }),
  })

  if (!response.ok) {
    throw new Error("Failed to query analytics")
  }

  return response.json()
}

export async function exportAnalytics(format: "csv" | "json", startDate: string, endDate: string) {
  const response = await fetch("/api/analytics/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format, startDate, endDate }),
  })

  if (!response.ok) {
    throw new Error("Failed to export analytics")
  }

  return response.blob()
}
