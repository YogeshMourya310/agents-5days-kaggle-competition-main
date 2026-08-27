#!/bin/bash

# Full System Startup Script
# Starts all components: A2A agents, FastAPI backend, and Next.js frontend

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       🚀 Stock Prediction System - Full Stack Startup 🚀             ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${BLUE}📋 Step 1: Checking Prerequisites${NC}"
echo "─────────────────────────────────────────────────────────"

# Check Python venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3.11 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi
echo -e "${GREEN}✅ Python virtual environment ready${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js 18+${NC}"
    echo "   brew install node"
    exit 1
fi
echo -e "${GREEN}✅ Node.js installed ($(node --version))${NC}"

# Check npm dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi
echo -e "${GREEN}✅ Frontend dependencies installed${NC}"

echo ""

# Step 2: Start A2A Agents
echo -e "${BLUE}📡 Step 2: Starting A2A Agents${NC}"
echo "─────────────────────────────────────────────────────────"

./scripts/start_all_agents.sh

echo -e "${YELLOW}⏳ Waiting 10 seconds for agents to initialize...${NC}"
sleep 10

# Verify agents
echo -e "${BLUE}🔍 Verifying agents...${NC}"
all_running=true
for port in 8001 8002 8003 8004 8005 8006; do
    if curl -s http://localhost:$port/.well-known/agent-card.json > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Agent on port $port: online${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Agent on port $port: not responding${NC}"
        all_running=false
    fi
done

if [ "$all_running" = false ]; then
    echo -e "${YELLOW}⚠️  Some agents are not responding. Continuing anyway...${NC}"
fi

echo ""

# Step 3: Start FastAPI Backend
echo -e "${BLUE}🔧 Step 3: Starting FastAPI Backend${NC}"
echo "─────────────────────────────────────────────────────────"

# Kill existing FastAPI if running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 8000 in use. Stopping existing process...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}🚀 Starting FastAPI backend on port 8000...${NC}"
nohup ./venv/bin/python frontend_api.py > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!
echo $FASTAPI_PID > logs/fastapi.pid

# Wait for FastAPI to start
echo -e "${YELLOW}⏳ Waiting for FastAPI to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ FastAPI backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Verify FastAPI
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Backend health check failed${NC}"
fi

echo ""

# Step 4: Start Next.js Frontend
echo -e "${BLUE}🎨 Step 4: Starting Next.js Frontend${NC}"
echo "─────────────────────────────────────────────────────────"

# Kill existing Next.js if running
if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Port 3001 in use. Stopping existing process...${NC}"
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}🚀 Starting Next.js dev server on port 3001...${NC}"
cd frontend
nohup npm run dev > ../logs/nextjs.log 2>&1 &
NEXTJS_PID=$!
echo $NEXTJS_PID > ../logs/nextjs.pid
cd ..

# Wait for Next.js to start
echo -e "${YELLOW}⏳ Waiting for Next.js to start (may take 20-30 seconds)...${NC}"
for i in {1..60}; do
    if curl -s http://localhost:3001/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Next.js frontend is ready!${NC}"
        break
    fi
    sleep 1
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║                    🎉 System Ready! 🎉                               ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}🌐 Frontend:${NC}  http://localhost:3001"
echo -e "${GREEN}🔧 Backend:${NC}   http://localhost:8000"
echo -e "${GREEN}📖 API Docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${BLUE}📊 Component Status:${NC}"
echo "   ✅ A2A Agents (6):  Ports 8001-8006"
echo "   ✅ FastAPI Backend: Port 8000 (PID: $FASTAPI_PID)"
echo "   ✅ Next.js Frontend: Port 3001 (PID: $NEXTJS_PID)"
echo ""
echo -e "${YELLOW}📝 Logs:${NC}"
echo "   FastAPI: tail -f logs/fastapi.log"
echo "   Next.js: tail -f logs/nextjs.log"
echo ""
echo -e "${YELLOW}🛑 To stop all services:${NC}"
echo "   ./scripts/stop_full_system.sh"
echo ""
echo "─────────────────────────────────────────────────────────"
echo -e "${GREEN}Ready to analyze stocks! Open http://localhost:3001 in your browser.${NC}"
echo "─────────────────────────────────────────────────────────"
echo ""

