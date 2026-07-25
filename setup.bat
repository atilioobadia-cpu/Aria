@echo off
title Aria Voice Assistant — Setup
echo ============================================
echo   Aria Voice Assistant — Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found:
python --version

REM Install dependencies
echo.
echo Installing Python packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install packages.
    pause
    exit /b 1
)
echo [OK] Packages installed.

REM Check Ollama
echo.
echo Checking for Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama not found.
    echo.
    echo Aria needs Ollama to run the AI brain locally.
    echo Download from: https://ollama.com
    echo After installing, pull a model:
    echo   ollama pull llama3.1:8b
    echo.
    echo For weaker PCs, use a smaller model:
    echo   ollama pull qwen2.5:7b
    echo   then edit config.yaml brain.model to "qwen2.5:7b"
) else (
    echo [OK] Ollama found:
    ollama --version
    echo.
    echo Checking if model is pulled...
    ollama list | findstr "llama3.1" >nul
    if %errorlevel% neq 0 (
        echo [INFO] Pulling llama3.1:8b model (this may take a while)...
        echo.
        ollama pull llama3.1:8b
    ) else (
        echo [OK] llama3.1:8b model found.
    )
)

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo To start Aria, run:
echo   python main.py
echo.
echo Then clap twice or say "Aria" to wake her.
echo.
pause
