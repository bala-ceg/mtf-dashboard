#!/bin/bash

# MTF Dashboard Startup Script
# This script starts the backend and frontend development servers

set -e

echo "🚀 Starting MTF Market Intelligence Dashboard..."

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running on localhost:5432"
    echo "Please start PostgreSQL and try again"
    exit 1
fi

echo "✅ PostgreSQL is running"

# Start backend
echo "📦 Starting FastAPI backend..."
cd backend
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Created .env file. Please update with your credentials."
fi

# Start backend in background
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

cd ..

# Start frontend
echo "📦 Starting React frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Start frontend in background
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

cd ..

echo ""
echo "=========================================="
echo "🎉 MTF Dashboard is now running!"
echo "=========================================="
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
