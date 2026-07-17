@echo off
cd /d "C:\Users\veeks\OneDrive\Desktop\ai-career-copilot"
echo Rebuilding backend...
docker-compose up -d --build backend
echo Done! Backend is rebuilding.
pause
