import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { format = "csv", startDate, endDate } = body

    // Generate mock export data
    const data = [
      { date: startDate, users: 150, matches: 450, documents: 120 },
      { date: endDate, users: 165, matches: 520, documents: 145 },
    ]

    if (format === "csv") {
      const csv = [
        "Date,Users,Matches,Documents",
        ...data.map((row) => `${row.date},${row.users},${row.matches},${row.documents}`),
      ].join("\n")

      return new NextResponse(csv, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": 'attachment; filename="analytics.csv"',
        },
      })
    } else if (format === "json") {
      return NextResponse.json(data)
    }

    return NextResponse.json({ error: "Invalid format" }, { status: 400 })
  } catch (error) {
    console.error("[v0] Export error:", error)
    return NextResponse.json({ error: "Failed to export data" }, { status: 500 })
  }
}
