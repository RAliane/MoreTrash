"use client"

import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import Link from "next/link"
import { Calendar, User } from "lucide-react"

export default function BlogPage() {
  const posts = [
    {
      id: 1,
      title: "How AI is Revolutionizing Professional Matching",
      excerpt: "Explore how artificial intelligence is changing the way professionals find their ideal matches.",
      author: "Sarah Chen",
      date: "Jan 15, 2025",
      category: "AI & Technology",
      image: "/ai-matching.jpg",
    },
    {
      id: 2,
      title: "5 Tips for Creating a Compelling Professional Profile",
      excerpt: "Learn how to showcase your skills and experience to attract better matches.",
      author: "Michael Rodriguez",
      date: "Jan 12, 2025",
      category: "Career Tips",
      image: "/professional-profile.png",
    },
    {
      id: 3,
      title: "Case Study: How Sarah Found Her Dream Team",
      excerpt: "A real story of how Matcher helped an entrepreneur build the perfect founding team.",
      author: "Alex Johnson",
      date: "Jan 10, 2025",
      category: "Success Stories",
      image: "/team-collaboration.png",
    },
    {
      id: 4,
      title: "The Future of Remote Work and Matching",
      excerpt: "How distributed teams are using AI matching to find better collaborators globally.",
      author: "Emma Watson",
      date: "Jan 8, 2025",
      category: "Industry Insights",
      image: "/remote-work-setup.png",
    },
  ]

  return (
    <main className="min-h-screen bg-background">
      <SiteHeader />

      {/* Header */}
      <section className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6">
            <span className="text-balance">Blog & Insights</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Stay updated with the latest news, tips, and insights about professional matching and career growth.
          </p>
        </div>
      </section>

      {/* Blog Posts Grid */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="grid md:grid-cols-2 gap-8">
            {posts.map((post) => (
              <article
                key={post.id}
                className="border border-border rounded-lg overflow-hidden hover:border-primary/50 transition group"
              >
                <div className="aspect-video bg-muted overflow-hidden">
                  <img
                    src={post.image || "/placeholder.svg"}
                    alt={post.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition"
                  />
                </div>

                <div className="p-6">
                  <div className="flex items-center gap-4 mb-3 text-sm text-muted-foreground">
                    <span className="bg-primary/10 text-primary px-3 py-1 rounded">{post.category}</span>
                  </div>

                  <Link href={`/blog/${post.id}`}>
                    <h2 className="text-xl font-bold text-foreground mb-2 hover:text-primary transition">
                      {post.title}
                    </h2>
                  </Link>

                  <p className="text-muted-foreground mb-4 line-clamp-2">{post.excerpt}</p>

                  <div className="flex items-center justify-between pt-4 border-t border-border text-sm text-muted-foreground">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        {post.author}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {post.date}
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Newsletter CTA */}
      <section className="bg-card border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">Subscribe to our newsletter</h2>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Get the latest articles, tips, and updates delivered to your inbox.
          </p>
          <div className="flex flex-col sm:flex-row gap-2 max-w-md mx-auto">
            <input
              type="email"
              placeholder="Enter your email"
              className="flex-1 px-4 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-muted-foreground"
            />
            <button className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition">
              Subscribe
            </button>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
