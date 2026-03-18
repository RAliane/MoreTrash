#!/bin/bash

echo "🎭 Starting MysteryiousHounslow Dummy Demo"
echo "=========================================="
echo ""

# Check if Docker or Podman is running
if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
    echo "🐳 Using Podman for container management"
    COMPOSE_CMD="podman-compose"
    DOCKER_CMD="podman"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "🐳 Using Docker for container management"
    COMPOSE_CMD="docker-compose"
    DOCKER_CMD="docker"
else
    echo "❌ Neither Podman nor Docker is running or available."
    echo "Please install and start Docker or Podman."
    exit 1
fi

echo "🏗️ Building containers..."
if ! $COMPOSE_CMD build; then
    echo "❌ Failed to build containers"
    echo "Check the build output above for errors."
    exit 1
fi

echo "🚀 Starting services..."
if ! $COMPOSE_CMD up -d; then
    echo "❌ Failed to start services"
    echo "Check if ports 3000, 5433, 8056 are available."
    exit 1
fi

echo ""
echo "⏳ Waiting for services to start..."
sleep 20  # Give more time for services to fully start

echo ""
echo "🔍 Checking service health..."

# Check database
if $DOCKER_CMD exec dummy-demo-db pg_isready -U postgres >/dev/null 2>&1; then
    echo "✅ Database: Ready (PostgreSQL + pgvector)"
else
    echo "❌ Database: Not ready"
fi

# Check Directus
if curl -s --max-time 10 http://localhost:8056/server/health >/dev/null 2>&1; then
    echo "✅ Directus: Ready (CMS/Admin panel)"
else
    echo "❌ Directus: Not ready (may take a few more minutes)"
fi

# Check web app
if curl -s --max-time 10 http://localhost:3000/health >/dev/null 2>&1; then
    echo "✅ Web App: Ready (Rust frontend)"
else
    echo "❌ Web App: Not ready (may take a few more minutes)"
fi

echo ""
echo "🎉 Dummy Demo Services Started!"
echo ""
echo "🌐 Access URLs:"
echo "  📱 Web App:     http://localhost:3000"
echo "  🛠️ Directus:    http://localhost:8056"
echo "  🐘 Database:    localhost:5433 (PostgreSQL)"
echo ""
echo "📊 Demo Data:"
echo "  - Database: postgres://postgres:demo123@localhost:5433/matchgorithm"
echo "  - Directus: admin@dummy-demo.co.uk / demo123"
echo ""
echo "🔍 Test Commands:"
echo "  curl http://localhost:3000/health"
echo "  curl http://localhost:3000/items"
echo "  curl 'http://localhost:3000/search?q=demo'"
echo ""
echo "🛑 To stop: $COMPOSE_CMD down"
echo "🧹 To clean: $COMPOSE_CMD down -v"