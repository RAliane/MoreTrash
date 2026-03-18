"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DocumentUploader } from "@/components/document-uploader"
import { MatchDisplay } from "@/components/match-display"
import { analyzeMatches } from "@/lib/matcher-service"
import { Sparkles, ArrowRight } from "lucide-react"

interface Match {
  candidateId: string
  score: number
  reasoning: string
  strengths: string[]
  alignments: string[]
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(false)
  const [documentId, setDocumentId] = useState<string | null>(null)

  const handleDocumentParsed = async (doc: any) => {
    setDocumentId(doc.id)
    // Automatically trigger matching
    await findMatches(doc.id)
  }

  const findMatches = async (docId: string) => {
    setLoading(true)
    try {
      // Placeholder candidate IDs - replace with actual candidates
      const candidateIds = ["cand_001", "cand_002", "cand_003", "cand_004", "cand_005"]

      const result = await analyzeMatches("user_123", docId, candidateIds)
      setMatches(result.matches || [])
    } catch (error) {
      console.error("[v0] Failed to find matches:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Find Your Perfect Match</h1>
        <p className="text-muted-foreground">Upload your profile and let our AI find ideal collaborators</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Upload Section */}
        <div className="md:col-span-1">
          <DocumentUploader onDocumentParsed={handleDocumentParsed} />
        </div>

        {/* Quick Stats */}
        <div className="md:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Your Matching Summary</CardTitle>
              <CardDescription>Overview of your profile and matches</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">{matches.length}</div>
                  <p className="text-xs text-muted-foreground mt-1">Matches Found</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {matches.length > 0 ? Math.round(matches.reduce((sum, m) => sum + m.score, 0) / matches.length) : 0}
                    %
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Avg Compatibility</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">{matches.filter((m) => m.score >= 80).length}</div>
                  <p className="text-xs text-muted-foreground mt-1">High Quality</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                How It Works
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
                  1
                </div>
                <div>
                  <p className="font-medium text-sm">Upload your profile</p>
                  <p className="text-xs text-muted-foreground">Resume, CV, or profile document</p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
                  2
                </div>
                <div>
                  <p className="font-medium text-sm">AI analysis</p>
                  <p className="text-xs text-muted-foreground">Extract skills and experience</p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
                  3
                </div>
                <div>
                  <p className="font-medium text-sm">Get matches</p>
                  <p className="text-xs text-muted-foreground">Ranked by compatibility</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Matches List */}
      {matches.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold text-foreground mb-4">Your Matches</h2>
          <div className="space-y-4">
            {matches.map((match, index) => (
              <MatchDisplay key={match.candidateId} match={match} rank={index + 1} />
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-r-transparent mx-auto mb-4" />
            <p className="text-muted-foreground">Finding perfect matches for you...</p>
          </div>
        </div>
      )}

      {!documentId && !loading && matches.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="pt-12 pb-12 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
              <ArrowRight className="w-6 h-6 text-primary" />
            </div>
            <h3 className="font-semibold text-lg mb-2">Get Started</h3>
            <p className="text-muted-foreground mb-6">Upload a document to begin finding your perfect matches</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
