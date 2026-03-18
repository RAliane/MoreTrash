export async function directusRequest(collection: string, method = "GET", data?: Record<string, any>) {
  try {
    const directusUrl = process.env.DIRECTUS_URL || "http://localhost:8055"
    const token = process.env.DIRECTUS_TOKEN || ""

    const response = await fetch(`${directusUrl}/items/${collection}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: data ? JSON.stringify(data) : undefined,
    })

    return await response.json()
  } catch (error) {
    console.error("[v0] Directus request error:", error)
    throw error
  }
}
