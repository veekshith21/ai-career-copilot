@echo off
cd /d "C:\Users\veeks\OneDrive\Desktop\ai-career-copilot"
echo Restarting backend...
docker compose restart backend
echo Backend restarted! Waiting for it to be ready...
timeout /t 8
echo Done.
pause
