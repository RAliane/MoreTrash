export const getStripeSecretKey = () => {
  const key = process.env.STRIPE_SECRET_KEY
  if (!key) {
    throw new Error("STRIPE_SECRET_KEY not configured")
  }
  return key
}

export const verifyStripeSignature = (body: string, signature: string) => {
  // This is a placeholder - use actual Stripe SDK
  console.log("[v0] Verifying Stripe signature")
  return true
}
