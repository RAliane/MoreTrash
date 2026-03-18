import { type NextRequest, NextResponse } from "next/server"

interface ParsedDocument {
  id: string
  fileName: string
  extractedText: string
  metadata: {
    uploadedAt: string
    fileType: string
    wordCount: number
  }
  skills: string[]
  experience: string[]
  summary: string
}

// Placeholder AI extraction - replace with actual LLM integration
function extractDocumentContent(text: string) {
  const skills = text.match(/(?:skills?|expertise|proficiencies?)[:\s]*([\w\s,]+)/gi) || []
  const experience = text.match(/(?:experience|background)[:\s]*([\w\s,]+)/gi) || []

  return {
    skills: skills.length > 0 ? ["Problem Solving", "Communication", "Leadership"] : [],
    experience: experience.length > 0 ? ["5+ years in tech", "Full-stack development"] : [],
    summary: text.substring(0, 500),
  }
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 })
    }

    const text = await file.text()
    const extracted = extractDocumentContent(text)

    const parsedDoc: ParsedDocument = {
      id: `doc_${Date.now()}`,
      fileName: file.name,
      extractedText: text,
      metadata: {
        uploadedAt: new Date().toISOString(),
        fileType: file.type,
        wordCount: text.split(/\s+/).length,
      },
      ...extracted,
    }

    return NextResponse.json(parsedDoc)
  } catch (error) {
    console.error("[v0] Document parsing error:", error)
    return NextResponse.json({ error: "Failed to parse document" }, { status: 500 })
  }
}
