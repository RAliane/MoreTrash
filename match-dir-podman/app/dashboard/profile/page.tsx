"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/lib/auth-context"
import { Mail, Award, MapPin } from "lucide-react"

export default function ProfilePage() {
  const { user } = useAuth()
  const [profile, setProfile] = useState({
    name: user?.name || "",
    email: user?.email || "",
    title: "Software Engineer",
    location: "San Francisco, CA",
    bio: "Full-stack developer passionate about building innovative solutions",
    skills: ["React", "Python", "Node.js", "Machine Learning"],
    experience: "5+ years",
  })

  const [editing, setEditing] = useState(false)

  const handleSave = () => {
    setEditing(false)
    console.log("[v0] Profile saved:", profile)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Your Profile</h1>
          <p className="text-muted-foreground mt-1">Manage your professional information</p>
        </div>
        <Button onClick={() => setEditing(!editing)} variant={editing ? "default" : "outline"}>
          {editing ? "Cancel" : "Edit Profile"}
        </Button>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card>
          <CardHeader>
            <CardTitle>Profile Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary text-2xl font-bold mx-auto">
              {profile.name.charAt(0)}
            </div>
            {editing ? (
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Name</label>
                  <Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Title</label>
                  <Input value={profile.title} onChange={(e) => setProfile({ ...profile, title: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Location</label>
                  <Input
                    value={profile.location}
                    onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                  />
                </div>
              </div>
            ) : (
              <div className="text-center">
                <h3 className="font-semibold">{profile.name}</h3>
                <p className="text-sm text-primary">{profile.title}</p>
                <p className="text-xs text-muted-foreground mt-1 flex items-center justify-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {profile.location}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Contact & Experience */}
        <Card>
          <CardHeader>
            <CardTitle>Contact & Experience</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Email
              </label>
              <p className="text-sm font-medium mt-1">{profile.email}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                <Award className="w-4 h-4" />
                Experience
              </label>
              <p className="text-sm font-medium mt-1">{profile.experience}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Bio</label>
              {editing ? (
                <textarea
                  value={profile.bio}
                  onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  className="w-full mt-1 p-2 border border-border rounded text-sm"
                  rows={3}
                />
              ) : (
                <p className="text-sm text-muted-foreground mt-1">{profile.bio}</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Skills */}
        <Card>
          <CardHeader>
            <CardTitle>Skills</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {profile.skills.map((skill) => (
                <Badge key={skill} variant="secondary">
                  {skill}
                </Badge>
              ))}
            </div>
            {editing && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">Add Skill</label>
                <div className="flex gap-2 mt-2">
                  <Input placeholder="Enter skill" className="text-sm" />
                  <Button size="sm" variant="outline">
                    Add
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {editing && (
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </div>
      )}
    </div>
  )
}
