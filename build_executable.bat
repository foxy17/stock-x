@echo off
echo ============================================
echo NSE Tracker - Building Executable
echo ============================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using global Python
)

echo.
echo Building executable with auto-py-to-exe...
echo.

REM Build using configuration file
auto-py-to-exe --config build_config.json --no-ui

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo The executable should be in the ./dist folder
echo.
echo To run manually:
echo   1. Navigate to ./dist/NSE-Tracker-Server/
echo   2. Run NSE-Tracker-Server.exe
echo.
echo The server will start on http://localhost:5127
echo Your React app can connect to this URL
echo.
pause 