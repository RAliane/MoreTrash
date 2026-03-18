# Directus Hooks

Custom hooks for Directus to extend functionality.

## Installation

Copy the hooks to your Directus extensions folder:

```bash
cp -r hooks/* /path/to/directus/extensions/hooks/
```

## Available Hooks

### match-created

Triggered when a new match is created. Sends notification to both users.

### profile-updated

Triggered when a user profile is updated. Recalculates potential matches.

### optimization-request

Triggered to send optimization requests to FastAPI service.

## Development

1. Create a new folder in `hooks/`
2. Add an `index.js` file with your hook logic
3. Restart Directus to load the hook
