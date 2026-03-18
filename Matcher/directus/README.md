# Directus Configuration

This folder contains configuration and setup instructions for Directus CMS.

## Quick Setup

1. **Get your Directus API Token**:
   - Log into your Directus admin panel (default: http://localhost:8055)
   - Go to **Settings** (gear icon) → **Access Tokens**
   - Click **Create Token**
   - Give it a name (e.g., "Matchgorithm App")
   - Set appropriate permissions (Admin for full access)
   - Copy the generated token

2. **Configure the token**:
   - Copy `../.env.example` to `../.env`
   - Set `DIRECTUS_TOKEN=your_token_here`

3. **For production (Podman secrets)**:
   ```bash
   echo "your_token_here" | podman secret create directus_token -
   ```

## Collections Schema

Import the schema from `schema.json` into your Directus instance:

```bash
# Using Directus CLI
npx directus schema apply ./directus/schema.json
```

### Required Collections

- `users` - User profiles (extends Directus users)
- `matches` - Match records between users
- `profiles` - Extended user profile data
- `organizations` - Company/organization data
- `jobs` - Job listings for matching
- `content` - CMS content (pages, blog posts)

## Hooks

Directus hooks are defined in `hooks/` and can be deployed to your Directus instance.

See `hooks/README.md` for hook documentation.
