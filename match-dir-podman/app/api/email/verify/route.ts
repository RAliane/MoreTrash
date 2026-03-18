import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json()

    if (!email || !email.includes("@")) {
      return NextResponse.json({ error: "Invalid email address" }, { status: 400 })
    }

    // In production, integrate with Hunter.io or Clearbit for email validation
    console.log("[v0] Email verification request:", email)

    return NextResponse.json({
      verified: true,
      email,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error("[v0] Email verification error:", error)
    return NextResponse.json({ error: "Failed to verify email" }, { status: 500 })
  }
}
