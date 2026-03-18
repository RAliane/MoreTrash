#!/bin/bash

echo "🎭 Starting MysteryiousHounslow Dummy Demo (Simplified)"
echo "======================================================"

# Simple test - just build and run the web service
echo "🏗️ Building web service..."
cd app
cargo build --release
cd ..

echo "🚀 Starting web service only..."
./app/target/release/dummy-demo-web &

WEB_PID=$!

echo ""
echo "⏳ Waiting for web service..."
sleep 2

echo ""
echo "🔍 Testing web service..."

# Test basic connectivity
if curl -s --max-time 2 http://localhost:3000/ >/dev/null 2>&1; then
    echo "✅ Web service is running!"
    echo ""
    echo "🌐 Test URLs:"
    echo "  curl http://localhost:3000/"
    echo "  curl http://localhost:3000/health"
    echo "  curl http://localhost:3000/items"
    echo ""
    echo "🛑 To stop: kill $WEB_PID"
else
    echo "❌ Web service failed to start"
    kill $WEB_PID 2>/dev/null
    exit 1
fi