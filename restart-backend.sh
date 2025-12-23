#!/bin/bash

# Script to kill existing backend processes and restart the backend server

echo "🛑 Stopping existing backend processes..."

# Kill any existing uvicorn processes running app.main
pkill -f "uvicorn.*app.main" 2>/dev/null

# Wait a moment for processes to terminate
sleep 2

# Check if any processes are still running
if pgrep -f "uvicorn.*app.main" > /dev/null; then
    echo "⚠️  Some processes still running, force killing..."
    pkill -9 -f "uvicorn.*app.main" 2>/dev/null
    sleep 1
fi

echo "✅ Backend processes stopped"

# Change to backend directory
cd "$(dirname "$0")/backend" || exit 1

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📦 Using virtual environment..."
    PYTHON_CMD="./venv/bin/python3"
elif [ -d ".venv" ]; then
    echo "📦 Using virtual environment..."
    PYTHON_CMD="./.venv/bin/python3"
else
    echo "⚠️  No virtual environment found, using system python3"
    PYTHON_CMD="python3"
fi

# Verify Python can import uvicorn
if ! $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
    echo "❌ Error: uvicorn not found. Please install dependencies:"
    echo "   cd backend && pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Starting backend server..."

# Start backend in background and redirect output to log file
nohup $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/nirnay-backend.log 2>&1 &

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend started successfully!"
    echo "📍 Backend URL: http://localhost:8000"
    echo "📝 Logs: tail -f /tmp/nirnay-backend.log"
    echo "🛑 To stop: pkill -f 'uvicorn.*app.main'"
else
    echo "❌ Backend failed to start. Check logs: tail -f /tmp/nirnay-backend.log"
    exit 1
fi

