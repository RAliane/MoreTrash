export async function hasuraQuery(query: string, variables?: Record<string, any>) {
  try {
    const response = await fetch(process.env.HASURA_GRAPHQL_ENDPOINT || "http://localhost:8080/v1/graphql", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-hasura-admin-secret": process.env.HASURA_ADMIN_SECRET || "",
      },
      body: JSON.stringify({ query, variables }),
    })

    const data = await response.json()
    return data
  } catch (error) {
    console.error("[v0] Hasura query error:", error)
    throw error
  }
}
