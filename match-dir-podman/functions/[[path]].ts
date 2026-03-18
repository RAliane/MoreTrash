export async function onRequest(context) {
  const { request } = context
  const url = new URL(request.url)

  // Handle API routes
  if (url.pathname.startsWith("/api/")) {
    return handleAPI(request, context)
  }

  // Serve static files or fallback to Next.js SSG
  return context.next(request)
}

async function handleAPI(request: Request, context: any) {
  const url = new URL(request.url)

  // Example API endpoint
  if (url.pathname === "/api/hello") {
    return new Response(
      JSON.stringify({
        message: "Hello from Matchgorithm API",
        platform: "Cloudflare Pages",
        timestamp: new Date().toISOString(),
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      },
    )
  }

  // Health check endpoint
  if (url.pathname === "/api/health") {
    return new Response(JSON.stringify({ status: "ok", service: "matchgorithm" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })
  }

  return new Response(JSON.stringify({ error: "Not Found" }), { status: 404 })
}
