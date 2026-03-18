// Client-side matcher service for interacting with the API

interface Document {
  id: string
  fileName: string
  extractedText: string
  skills: string[]
  experience: string[]
}

interface Match {
  candidateId: string
  score: number
  reasoning: string
  strengths: string[]
  alignments: string[]
}

export async function parseDocument(file: File): Promise<Document> {
  const formData = new FormData()
  formData.append("file", file)

  const response = await fetch("/api/documents/parse", {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error("Failed to parse document")
  }

  return response.json()
}

export async function analyzeMatches(userId: string, documentId: string, candidateIds: string[]) {
  const response = await fetch("/api/matcher/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      userId,
      documentId,
      candidateIds,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to analyze matches")
  }

  return response.json()
}

export async function compareProfiles(profile1Id: string, profile2Id: string) {
  const response = await fetch("/api/matcher/compare", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      profile1Id,
      profile2Id,
    }),
  })

  if (!response.ok) {
    throw new Error("Failed to compare profiles")
  }

  return response.json()
}
