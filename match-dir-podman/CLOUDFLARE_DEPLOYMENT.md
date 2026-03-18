# Matchgorithm - Cloudflare Pages Deployment Guide

## Prerequisites
- Cloudflare account with a registered domain
- Node.js 18+ and npm/pnpm installed
- Wrangler CLI: `npm install -g wrangler`

## Local Development

\`\`\`bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Test Cloudflare Pages locally
npx wrangler pages dev dist
\`\`\`

## Deployment Steps

### 1. Create Cloudflare Pages Project

\`\`\`bash
# Login to Cloudflare
wrangler login

# Deploy to Cloudflare Pages
npm run build
wrangler pages deploy dist
\`\`\`

### 2. Configure Environment Variables

In Cloudflare Dashboard:
1. Go to Pages → matchgorithm → Settings → Environment variables
2. Add the following variables:

\`\`\`
NEXT_PUBLIC_API_URL=https://matchgorithm.co.uk/api
NEXT_PUBLIC_APP_URL=https://matchgorithm.co.uk
\`\`\`

### 3. Set Custom Domain

1. Go to Pages → matchgorithm → Custom domains
2. Add `matchgorithm.co.uk`
3. Update DNS records to point to Cloudflare nameservers

### 4. Enable Functions (Optional)

For advanced API routes:
\`\`\`bash
wrangler pages functions build
\`\`\`

## Project Structure

\`\`\`
matchgorithm/
├── app/                  # Next.js app directory (all pages)
├── components/           # React components
├── public/              # Static assets, robots.txt, llm.txt
├── functions/           # Cloudflare Pages Functions
├── wrangler.toml        # Cloudflare configuration
├── wrangler.jsonc       # Alternative Cloudflare config
├── next.config.mjs      # Next.js configuration (static export)
└── tsconfig.json        # TypeScript configuration
\`\`\`

## Features

- ✅ **Static Export**: Fully static site optimized for Cloudflare Pages
- ✅ **API Routes**: Cloudflare Functions support at `/api/*`
- ✅ **Environment Variables**: Support for `.env.local` and Cloudflare bindings
- ✅ **Sitemap & SEO**: Automatic sitemap generation at `/sitemap.xml`
- ✅ **Robots.txt**: Search engine optimization configured
- ✅ **llm.txt**: Machine-readable documentation
- ✅ **Open Graph**: Social media preview optimization
- ✅ **Dark Mode**: Theme switching with next-themes

## Performance Optimizations

- Image optimization (unoptimized for Cloudflare compatibility)
- CSS minification via Tailwind CSS v4
- Tree-shaking and code splitting
- DNS prefetching for external resources
- Lazy loading for components

## Monitoring & Analytics

View deployment status:
\`\`\`bash
wrangler pages deployment list
\`\`\`

Check build logs:
\`\`\`bash
wrangler pages deployment tail
\`\`\`

## Troubleshooting

### Issue: Static export fails
**Solution**: Ensure all pages use `export default` and no server-side rendering

### Issue: API routes not working
**Solution**: Verify `functions/[[path]].ts` exists and wrangler.toml is configured

### Issue: Environment variables not loading
**Solution**: Rebuild after adding variables to Cloudflare Dashboard

## Deployment Checklist

- [ ] All pages render statically
- [ ] No dynamic server routes in app directory
- [ ] API endpoints configured in `functions/`
- [ ] Environment variables added to Cloudflare
- [ ] Domain configured and DNS updated
- [ ] robots.txt and llm.txt in public/
- [ ] Sitemap generates correctly
- [ ] Open Graph tags present
- [ ] Performance is optimized

## Support

For issues, visit:
- Cloudflare Pages Docs: https://developers.cloudflare.com/pages/
- Next.js Static Export: https://nextjs.org/docs/app/building-your-application/deploying/static-exports
