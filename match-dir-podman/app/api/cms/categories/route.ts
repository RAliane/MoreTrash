import { NextResponse } from "next/server"

interface Category {
  id: string
  name: string
  slug: string
  description: string
  itemCount: number
}

const categories: Category[] = [
  {
    id: "cat-1",
    name: "Guides",
    slug: "guides",
    description: "Step-by-step guides and tutorials",
    itemCount: 12,
  },
  {
    id: "cat-2",
    name: "Blog",
    slug: "blog",
    description: "Latest news and insights",
    itemCount: 28,
  },
  {
    id: "cat-3",
    name: "FAQ",
    slug: "faq",
    description: "Frequently asked questions",
    itemCount: 15,
  },
]

export async function GET() {
  try {
    return NextResponse.json(categories)
  } catch (error) {
    console.error("[v0] Categories fetch error:", error)
    return NextResponse.json({ error: "Failed to fetch categories" }, { status: 500 })
  }
}
