import { type NextRequest, NextResponse } from "next/server"

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

// Placeholder content store - integrate with Directus API
const contentStore: Record<string, ContentItem> = {
  "article-1": {
    id: "article-1",
    title: "Getting Started with AI Matching",
    slug: "getting-started-ai-matching",
    content: "Learn how to use our AI matching platform to find the perfect collaborators...",
    status: "published",
    category: "guides",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-15T00:00:00Z",
  },
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const id = searchParams.get("id")
    const slug = searchParams.get("slug")
    const category = searchParams.get("category")

    let result
    if (id) {
      result = contentStore[id]
    } else if (slug) {
      result = Object.values(contentStore).find((item) => item.slug === slug)
    } else if (category) {
      result = Object.values(contentStore).filter((item) => item.category === category && item.status === "published")
    } else {
      result = Object.values(contentStore).filter((item) => item.status === "published")
    }

    if (!result) {
      return NextResponse.json({ error: "Content not found" }, { status: 404 })
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error("[v0] Content fetch error:", error)
    return NextResponse.json({ error: "Failed to fetch content" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: Omit<ContentItem, "id" | "createdAt" | "updatedAt"> = await request.json()

    const newItem: ContentItem = {
      id: `article-${Date.now()}`,
      ...body,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }

    contentStore[newItem.id] = newItem
    return NextResponse.json(newItem, { status: 201 })
  } catch (error) {
    console.error("[v0] Content creation error:", error)
    return NextResponse.json({ error: "Failed to create content" }, { status: 500 })
  }
}
