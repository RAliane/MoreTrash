#!/bin/bash

echo "🎭 MysteryiousHounslow Dummy Demo - Local Version"
echo "================================================="

# Build the Rust application locally
echo "🏗️ Building Rust web server..."
cd app
cargo build --release
cd ..

if [ ! -f "app/target/release/dummy-demo-web" ]; then
    echo "❌ Build failed. Please ensure Rust is installed."
    echo "Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

echo "🚀 Starting web server..."
./app/target/release/dummy-demo-web &
WEB_PID=$!

echo ""
echo "⏳ Waiting for server to start..."
sleep 2

echo ""
echo "🔍 Testing endpoints..."

# Test basic endpoints
echo "Testing root endpoint:"
curl -s http://localhost:3000/ | head -5

echo ""
echo "Testing health endpoint:"
curl -s http://localhost:3000/health | head -10

echo ""
echo "Testing items endpoint:"
curl -s http://localhost:3000/items | head -10

echo ""
echo "Testing search endpoint:"
curl -s "http://localhost:3000/search?q=demo&limit=2" | head -10

echo ""
echo "🎉 Demo is running!"
echo ""
echo "🌐 Access URLs:"
echo "  📄 Root:    http://localhost:3000/"
echo "  🏥 Health:  http://localhost:3000/health"
echo "  📦 Items:   http://localhost:3000/items"
echo "  🔍 Search:  http://localhost:3000/search?q=demo"
echo ""
echo "🛑 To stop: kill $WEB_PID"
echo "📝 The server demonstrates hybrid kNN functionality with mock data"