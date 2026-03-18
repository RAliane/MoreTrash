"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, AlertCircle } from "lucide-react"

interface MatchDisplayProps {
  match: {
    candidateId: string
    score: number
    reasoning: string
    strengths: string[]
    alignments: string[]
  }
  rank?: number
}

export function MatchDisplay({ match, rank }: MatchDisplayProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600"
    if (score >= 60) return "text-yellow-600"
    return "text-red-600"
  }

  return (
    <Card className="hover:shadow-md transition">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              {rank && <Badge variant="outline">#{rank}</Badge>}
              Candidate {match.candidateId.slice(-4)}
            </CardTitle>
            <CardDescription>{match.reasoning}</CardDescription>
          </div>
          <div className={`text-3xl font-bold ${getScoreColor(match.score)}`}>{match.score}%</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-600" />
            Strengths
          </h4>
          <div className="flex flex-wrap gap-2">
            {match.strengths.map((strength) => (
              <Badge key={strength} variant="secondary">
                {strength}
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-blue-600" />
            Alignments
          </h4>
          <div className="flex flex-wrap gap-2">
            {match.alignments.map((alignment) => (
              <Badge key={alignment} variant="outline">
                {alignment}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
