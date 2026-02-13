@echo off
REM Build Chess Explorer Windows Executable

echo ================================================
echo    Building Chess Explorer Windows Executable
echo ================================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Build the executable
echo.
echo Building executable...
echo.
pyinstaller ChessExplorer.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Create distribution folder
echo.
echo Creating distribution package...
if not exist "dist\ChessExplorer_Release" mkdir "dist\ChessExplorer_Release"

REM Copy files
copy "dist\ChessExplorer.exe" "dist\ChessExplorer_Release\" >nul
copy "EXECUTABLE_README.txt" "dist\ChessExplorer_Release\README.txt" >nul
if not exist "dist\ChessExplorer_Release\games" mkdir "dist\ChessExplorer_Release\games"

echo.
echo ================================================
echo    BUILD COMPLETE!
echo ================================================
echo.
echo Executable created: dist\ChessExplorer_Release\ChessExplorer.exe
echo.
echo To distribute:
echo   1. Zip the entire "dist\ChessExplorer_Release" folder
echo   2. Share the zip file
echo   3. Users just double-click ChessExplorer.exe!
echo.
echo To test: cd dist\ChessExplorer_Release ^&^& ChessExplorer.exe
echo.
pause
