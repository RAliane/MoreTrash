#!/bin/bash

# Check if the app already exists
if [ ! -d "/usr/src/app/nextjs-dashboard" ]; then
  echo "Initializing Next.js app..."
  npm install -g pnpm
  npx create-next-app@latest nextjs-dashboard --example "https://github.com/vercel/next-learn/tree/main/dashboard/starter-example" --use-pnpm
else
  echo "Next.js app already exists. Skipping initialization."
fi

# Execute the default entry point (or your specific command)
exec "$@"
