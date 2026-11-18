@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
pushd "%SCRIPT_DIR%" >nul
if errorlevel 1 (
    echo ERROR: Could not open the folder containing this batch file.
    goto :fail_no_pop
)

if not exist "%SCRIPT_DIR%\netmonitor.py" (
    echo ERROR: netmonitor.py was not found beside this batch file.
    goto :fail
)
if not exist "%SCRIPT_DIR%\config.ini" (
    echo ERROR: config.ini was not found beside this batch file.
    goto :fail
)

call :find_python
if defined PYTHON_EXE goto :python_found

where winget >nul 2>nul
if errorlevel 1 (
    echo Python was not found, and Windows Package Manager ^(winget^) is unavailable.
    echo Install Python 3.13 from https://www.python.org/downloads/windows/ and run this file again.
    goto :fail
)

echo Python was not found. Installing Python 3.13 for the current Windows user...
winget install --id Python.Python.3.13 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo ERROR: Python installation failed.
    goto :fail
)

for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~fD\python.exe" set "PYTHON_EXE=%%~fD\python.exe"
)
if not defined PYTHON_EXE call :find_python
if not defined PYTHON_EXE (
    echo Python was installed, but this command window cannot locate it.
    echo Close this window and run build_networkmonitor.bat again.
    goto :fail
)

:python_found
echo Using Python:
"%PYTHON_EXE%" --version
if errorlevel 1 goto :fail

"%PYTHON_EXE%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo Setting up Python package installer...
    "%PYTHON_EXE%" -m ensurepip --upgrade
    if errorlevel 1 goto :fail
)

"%PYTHON_EXE%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    "%PYTHON_EXE%" -m pip install pyinstaller
    if errorlevel 1 goto :fail
)

echo Building the standalone executable...
"%PYTHON_EXE%" -m PyInstaller --clean --onefile --console --name NetworkMonitor --distpath "%SCRIPT_DIR%\dist" --workpath "%SCRIPT_DIR%\build" --specpath "%SCRIPT_DIR%" "%SCRIPT_DIR%\netmonitor.py"
if errorlevel 1 goto :fail

if not exist "%SCRIPT_DIR%\dist" mkdir "%SCRIPT_DIR%\dist"
copy /Y "%SCRIPT_DIR%\config.ini" "%SCRIPT_DIR%\dist\config.ini" >nul
if errorlevel 1 (
    echo ERROR: The executable was built, but config.ini could not be copied to dist.
    goto :fail
)

echo.
echo Build complete:
echo   "%SCRIPT_DIR%\dist\NetworkMonitor.exe"
echo   "%SCRIPT_DIR%\dist\config.ini"
echo.
echo SHA-256 of NetworkMonitor.exe:
certutil -hashfile "%SCRIPT_DIR%\dist\NetworkMonitor.exe" SHA256
if errorlevel 1 goto :fail
popd
pause
exit /b 0

:find_python
set "PYTHON_EXE="
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
)
if defined PYTHON_EXE exit /b 0

where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
)
exit /b 0

:fail
popd
:fail_no_pop
echo.
echo Build failed. Review the error above.
pause
exit /b 1
