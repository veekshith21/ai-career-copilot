@echo off
cd /d "C:\Users\veeks\OneDrive\Desktop\ai-career-copilot"
echo Starting all services...
docker compose up -d
echo All services started!
timeout /t 5
docker compose logs --tail=20 backend
pause
