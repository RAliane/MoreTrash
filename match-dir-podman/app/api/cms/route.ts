import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  try {
    const collection = request.nextUrl.searchParams.get("collection")

    if (!collection) {
      return NextResponse.json({ error: "Collection parameter required" }, { status: 400 })
    }

    const directusUrl = process.env.DIRECTUS_URL || "http://localhost:8055"
    const token = process.env.DIRECTUS_TOKEN || ""

    const response = await fetch(`${directusUrl}/items/${collection}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[v0] CMS read error:", error)
    return NextResponse.json({ error: "Failed to read CMS data" }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const { collection, data } = await request.json()

    if (!collection || !data) {
      return NextResponse.json({ error: "Collection and data required" }, { status: 400 })
    }

    const directusUrl = process.env.DIRECTUS_URL || "http://localhost:8055"
    const token = process.env.DIRECTUS_TOKEN || ""

    const response = await fetch(`${directusUrl}/items/${collection}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    })

    const result = await response.json()
    return NextResponse.json(result, { status: response.status })
  } catch (error) {
    console.error("[v0] CMS create error:", error)
    return NextResponse.json({ error: "Failed to create CMS entry" }, { status: 500 })
  }
}
