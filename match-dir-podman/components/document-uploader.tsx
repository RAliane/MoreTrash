"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { parseDocument } from "@/lib/matcher-service"
import { Upload, File } from "lucide-react"

interface DocumentUploaderProps {
  onDocumentParsed?: (doc: any) => void
}

export function DocumentUploader({ onDocumentParsed }: DocumentUploaderProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [parsedData, setParsedData] = useState<any | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file")
      return
    }

    setUploading(true)
    try {
      const data = await parseDocument(file)
      setParsedData(data)
      onDocumentParsed?.(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Document</CardTitle>
        <CardDescription>Upload your resume or profile document for AI analysis</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="bg-destructive/10 border border-destructive text-destructive px-3 py-2 rounded text-sm">
            {error}
          </div>
        )}

        <div className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary transition">
          <input type="file" onChange={handleFileChange} accept=".pdf,.txt,.docx" className="hidden" id="file-input" />
          <label htmlFor="file-input" className="cursor-pointer">
            <div className="space-y-2">
              <Upload className="w-8 h-8 mx-auto text-muted-foreground" />
              <p className="text-sm font-medium">{file ? file.name : "Drag and drop or click to select"}</p>
              <p className="text-xs text-muted-foreground">PDF, TXT, or DOCX</p>
            </div>
          </label>
        </div>

        <Button onClick={handleUpload} disabled={!file || uploading} className="w-full">
          {uploading ? "Uploading..." : "Upload & Analyze"}
        </Button>

        {parsedData && (
          <div className="border border-border rounded-lg p-4 space-y-3">
            <h3 className="font-semibold flex items-center gap-2">
              <File className="w-4 h-4" />
              Document Analyzed
            </h3>
            <div className="space-y-2 text-sm">
              <p>
                <span className="font-medium">Skills detected:</span> {parsedData.skills?.join(", ") || "None"}
              </p>
              <p>
                <span className="font-medium">Word count:</span> {parsedData.metadata?.wordCount}
              </p>
              <p>
                <span className="font-medium">Uploaded:</span>{" "}
                {new Date(parsedData.metadata?.uploadedAt).toLocaleDateString()}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
