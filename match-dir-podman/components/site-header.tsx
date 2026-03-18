"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Menu, X } from "lucide-react"
import { useState } from "react"

export function SiteHeader() {
  const [isOpen, setIsOpen] = useState(false)

  const navLinks = [
    { href: "/platform", label: "Platform" },
    { href: "/pricing", label: "Pricing" },
    { href: "/solutions", label: "Solutions" },
    { href: "/blog", label: "Blog" },
    { href: "/about", label: "About" },
    { href: "/docs", label: "Docs" },
    { href: "/api-docs", label: "API" },
  ]

  return (
    <header className="border-b border-border sticky top-0 z-50 bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        {/* Updated logo text from "Matcher" to "Matchgorithm" */}
        <Link href="/" className="text-2xl font-bold text-primary">
          Matchgorithm
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex gap-8 items-center">
          {navLinks.map((link) => (
            <Link key={link.href} href={link.href} className="text-foreground hover:text-primary transition text-sm">
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Desktop Buttons */}
        <div className="hidden md:flex gap-4 items-center">
          <Link href="/auth/sign-in">
            <Button variant="outline" size="sm">
              Log In
            </Button>
          </Link>
          <Link href="/auth/sign-up">
            <Button size="sm">Get Started</Button>
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <button className="md:hidden p-2" onClick={() => setIsOpen(!isOpen)} aria-label="Toggle menu">
          {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Navigation */}
      {isOpen && (
        <div className="md:hidden border-t border-border bg-card">
          <nav className="flex flex-col gap-4 p-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-foreground hover:text-primary transition text-sm py-2"
              >
                {link.label}
              </Link>
            ))}
            <div className="flex flex-col gap-2 pt-4 border-t border-border">
              <Link href="/auth/sign-in">
                <Button variant="outline" className="w-full bg-transparent">
                  Log In
                </Button>
              </Link>
              <Link href="/auth/sign-up">
                <Button className="w-full">Get Started</Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  )
}
