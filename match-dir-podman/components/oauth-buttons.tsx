"use client"

import { Button } from "@/components/ui/button"
import { Chrome, Github, Wind as Windows } from "lucide-react"

interface OAuthButtonsProps {
  isLoading?: boolean
  onOAuthClick?: (provider: string) => void
}

export function OAuthButtons({ isLoading = false, onOAuthClick }: OAuthButtonsProps) {
  const handleOAuthClick = (provider: string) => {
    console.log("[v0] OAuth flow initiated for:", provider)
    if (onOAuthClick) {
      onOAuthClick(provider)
    }
    // In production, this would redirect to the OAuth provider
    // window.location.href = `/api/auth/oauth/${provider}`
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-background text-muted-foreground">Or continue with</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Button variant="outline" onClick={() => handleOAuthClick("google")} disabled={isLoading} className="w-full">
          <Chrome className="w-4 h-4" />
          <span className="sr-only">Sign in with Google</span>
        </Button>

        <Button variant="outline" onClick={() => handleOAuthClick("github")} disabled={isLoading} className="w-full">
          <Github className="w-4 h-4" />
          <span className="sr-only">Sign in with GitHub</span>
        </Button>

        <Button variant="outline" onClick={() => handleOAuthClick("microsoft")} disabled={isLoading} className="w-full">
          <Windows className="w-4 h-4" />
          <span className="sr-only">Sign in with Microsoft</span>
        </Button>
      </div>
    </div>
  )
}
