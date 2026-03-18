import { type NextRequest, NextResponse } from "next/server"
import { headers } from "next/headers"

export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const headersList = await headers()
    const signature = headersList.get("stripe-signature") || ""

    // In production, use stripe.webhooks.constructEvent()
    console.log("[v0] Stripe webhook received")

    const event = JSON.parse(body)

    switch (event.type) {
      case "payment_intent.succeeded":
        console.log("[v0] Payment succeeded:", event.data.object.id)
        // Process successful payment
        break
      case "customer.subscription.created":
        console.log("[v0] Subscription created:", event.data.object.id)
        // Handle new subscription
        break
      case "invoice.payment_failed":
        console.log("[v0] Payment failed:", event.data.object.id)
        // Handle failed payment
        break
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error("[v0] Stripe webhook error:", error)
    return NextResponse.json({ error: "Webhook processing failed" }, { status: 400 })
  }
}
