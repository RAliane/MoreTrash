// OAuth configuration for multiple providers

export const oauthProviders = {
  google: {
    name: "Google",
    icon: "Google",
    scope: "openid profile email",
  },
  github: {
    name: "GitHub",
    icon: "Github",
    scope: "user:email",
  },
  microsoft: {
    name: "Microsoft",
    icon: "Windows",
    scope: "openid profile email",
  },
}

export type OAuthProvider = keyof typeof oauthProviders
