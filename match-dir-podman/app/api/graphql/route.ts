import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // const token = request.headers.get("authorization")?.replace("Bearer ", "")

    const hasuraUrl = process.env.HASURA_GRAPHQL_ENDPOINT || "http://localhost:8080/v1/graphql"

    const response = await fetch(hasuraUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-hasura-admin-secret": process.env.HASURA_ADMIN_SECRET || "",
        // "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    const responseData = await response.json()

    return NextResponse.json(responseData, { status: response.status })
  } catch (error) {
    console.error("[v0] GraphQL proxy error:", error)
    return NextResponse.json({ errors: [{ message: "GraphQL proxy failed" }] }, { status: 500 })
  }
}
