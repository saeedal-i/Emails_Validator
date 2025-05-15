@echo off
echo ===== Email Validator GitHub Push Script =====
echo.

REM Check if Git is installed
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Git is not installed or not in your PATH.
    echo Please install Git from https://git-scm.com/downloads
    echo and run this script again.
    pause
    exit /b 1
)

echo Setting up Git repository...
echo.

REM Initialize Git repository if not already initialized
if not exist .git (
    git init
    echo Git repository initialized.
) else (
    echo Git repository already exists.
)

echo.
echo Please enter your Git user information:
set /p GIT_USERNAME="Your Name: "
set /p GIT_EMAIL="Your Email: "

REM Configure Git
git config --global user.name "%GIT_USERNAME%"
git config --global user.email "%GIT_EMAIL%"
echo Git configured with your identity.

echo.
echo Adding files to Git...
git add .
echo Files added to Git.

echo.
echo Creating initial commit...
git commit -m "Initial commit"
echo Initial commit created.

echo.
echo Please enter your GitHub information:
set /p GITHUB_USERNAME="GitHub Username: "
set /p REPO_NAME="Repository Name (e.g., email-validator): "

echo.
echo Connecting to GitHub...
git remote add origin https://github.com/%GITHUB_USERNAME%/%REPO_NAME%.git
git branch -M main

echo.
echo Ready to push to GitHub.
echo NOTE: You will be prompted for your GitHub credentials.
echo If you have 2FA enabled, use a Personal Access Token instead of your password.
echo.
echo Press any key to continue with the push...
pause >nul

git push -u origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo Successfully pushed to GitHub!
    echo Your repository is now available at: https://github.com/%GITHUB_USERNAME%/%REPO_NAME%
) else (
    echo There was an issue pushing to GitHub.
    echo Please check your credentials and try again.
)

echo.
echo Script completed.
pause