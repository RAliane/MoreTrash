// Hook: optimization-request
// Sends optimization requests to FastAPI XGBoost service

module.exports = function registerHook({ filter, action }) {
  // When optimization is requested via custom endpoint
  action("custom.optimize", async ({ payload }, { env }) => {
    const FASTAPI_URL = env.FASTAPI_URL || "http://fastapi:8001"

    try {
      const response = await fetch(`${FASTAPI_URL}/api/v1/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      const result = await response.json()
      console.log(`[Matchgorithm] Optimization request submitted: ${result.request_id}`)

      return result
    } catch (error) {
      console.error(`[Matchgorithm] Optimization request failed:`, error)
      throw error
    }
  })
}
