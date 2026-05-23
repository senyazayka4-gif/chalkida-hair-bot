@echo off
title Push Bot to GitHub
echo ===================================================
echo   🚀 Preparing to Deploy Chalkida Hair Bot to GitHub 🚀
echo ===================================================
echo.
echo 1. Go to https://github.com and log in.
echo 2. Click "New" (or "+" -> "New repository") to create a repository.
echo 3. Name it (e.g., "chalkida-hair-bot") and make it Private or Public.
echo 4. Leave "Add a README", "Add .gitignore", and "Choose a license" UNCHECKED (empty).
echo 5. Click "Create repository".
echo.
echo ---------------------------------------------------
set /p REPO_URL="Paste your GitHub Repository HTTPS URL (e.g. https://github.com/username/repo.git): "
if "%REPO_URL%"=="" (
    echo [ERROR] Repository URL cannot be empty!
    pause
    exit /b
)
echo.
echo Configuring Git remotes...
git remote remove github >nul 2>&1
git remote add github %REPO_URL%
echo.
echo Pushing code to GitHub...
git branch -M main
git push -u github main
echo.
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed! Please ensure you copied the URL correctly and are logged in to Git.
) else (
    echo.
    echo 🎉 SUCCESS: Code successfully pushed to GitHub!
    echo.
    echo What to do next:
    echo 1. Go to https://dashboard.render.com
    echo 2. Click "New +" -> "Web Service"
    echo 3. Connect your GitHub account and select your "chalkida-hair-bot" repository.
    echo 4. Set the environment variables in the "Environment" tab:
    echo    - BOT_TOKEN
    echo    - ADMIN_IDS
    echo    - GEMINI_API_KEY
    echo    - DB_URL
    echo 5. Click "Deploy Web Service"!
)
pause
