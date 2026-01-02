@echo off
echo Connecting to Remote Server...
ssh -t administrator@69.197.145.4 "docker logs -f ai-presentation-api-1"
pause
