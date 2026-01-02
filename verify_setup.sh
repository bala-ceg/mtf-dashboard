#!/bin/bash

# MTF Dashboard Verification Script
# Checks if all components are properly configured and ready to run

set -e

echo "🔍 MTF Dashboard Setup Verification"
echo "===================================="
echo ""

ERRORS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        ((ERRORS++))
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${YELLOW}⚠${NC} $1 is missing"
        ((ERRORS++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${RED}✗${NC} $1 is missing"
        ((ERRORS++))
    fi
}

# 1. Check system dependencies
echo "1. System Dependencies:"
check_command python3
check_command node
check_command npm
check_command psql
check_command docker
check_command docker-compose
echo ""

# 2. Check Python version
echo "2. Python Version:"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ $(echo -e "$PYTHON_VERSION\n3.11" | sort -V | head -n1) == "3.11" ]] || [[ "$PYTHON_VERSION" == "3.11"* ]]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (>= 3.11)"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (need >= 3.11)"
    ((ERRORS++))
fi
echo ""

# 3. Check Node version
echo "3. Node.js Version:"
NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
if [[ $(echo -e "$NODE_VERSION\n18.0.0" | sort -V | head -n1) == "18.0.0" ]]; then
    echo -e "${GREEN}✓${NC} Node.js $NODE_VERSION (>= 18)"
else
    echo -e "${RED}✗${NC} Node.js $NODE_VERSION (need >= 18)"
    ((ERRORS++))
fi
echo ""

# 4. Check PostgreSQL
echo "4. PostgreSQL:"
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running on localhost:5432"
    
    # Check if database exists
    if psql -U bseetharaman -lqt | cut -d \| -f 1 | grep -qw mtf_db; then
        echo -e "${GREEN}✓${NC} Database 'mtf_db' exists"
    else
        echo -e "${YELLOW}⚠${NC} Database 'mtf_db' does not exist"
        echo "  Run: psql -U bseetharaman -c 'CREATE DATABASE mtf_db;'"
    fi
else
    echo -e "${RED}✗${NC} PostgreSQL is NOT running"
    ((ERRORS++))
fi
echo ""

# 5. Check project structure
echo "5. Project Structure:"
check_dir "backend"
check_dir "backend/app"
check_dir "backend/app/routers"
check_dir "frontend"
check_dir "frontend/src"
check_dir "sql"
check_dir "etl"
echo ""

# 6. Check backend files
echo "6. Backend Files:"
check_file "backend/requirements.txt"
check_file "backend/app/main.py"
check_file "backend/app/config.py"
check_file "backend/app/database.py"
check_file "backend/app/models.py"
check_file "backend/app/routers/market.py"
check_file "backend/app/routers/stocks.py"
check_file "backend/app/routers/shockers.py"
echo ""

# 7. Check frontend files
echo "7. Frontend Files:"
check_file "frontend/package.json"
check_file "frontend/vite.config.js"
check_file "frontend/src/main.jsx"
check_file "frontend/src/App.jsx"
check_file "frontend/src/api/client.js"
echo ""

# 8. Check SQL files
echo "8. SQL Files:"
check_file "sql/01_create_tables.sql"
check_file "sql/02_market_overview_stats.sql"
check_file "sql/03_market_flow_stats.sql"
check_file "sql/05_top_mtf_gainers_latest.sql"
check_file "sql/06_top_mtf_losers_latest.sql"
echo ""

# 9. Check environment files
echo "9. Environment Configuration:"
if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓${NC} backend/.env exists"
else
    echo -e "${YELLOW}⚠${NC} backend/.env is missing (will use .env.example)"
    check_file "backend/.env.example"
fi

if [ -f "frontend/.env" ]; then
    echo -e "${GREEN}✓${NC} frontend/.env exists"
else
    echo -e "${YELLOW}⚠${NC} frontend/.env is missing (will use .env.example)"
    check_file "frontend/.env.example"
fi
echo ""

# 10. Check documentation
echo "10. Documentation:"
check_file "README_DASHBOARD.md"
check_file "DEVELOPMENT_GUIDE.md"
check_file "QUICKSTART.md"
check_file "docker-compose.yml"
echo ""

# Summary
echo "===================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Your MTF Dashboard is ready to run!"
    echo ""
    echo "Next steps:"
    echo "  1. Start backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "  2. Start frontend: cd frontend && npm run dev"
    echo "  3. Or use Docker:  docker-compose up -d"
    echo ""
    echo "📚 Documentation:"
    echo "  - Quick Start: QUICKSTART.md"
    echo "  - Full Guide:  README_DASHBOARD.md"
    echo "  - Dev Guide:   DEVELOPMENT_GUIDE.md"
else
    echo -e "${RED}❌ Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Please fix the issues above before running the dashboard."
    echo "Refer to QUICKSTART.md for setup instructions."
fi
echo "===================================="
