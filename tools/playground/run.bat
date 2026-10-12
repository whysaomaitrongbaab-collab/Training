@echo off
echo Starting Destrier Lab Playground...
python -m uvicorn server:app --host 127.0.0.1 --port 8888 --reload
pause
