@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ==========================================
echo     Safarnama - starting up
echo  ==========================================
echo.

REM ---------------------------------------------------------------
REM  1. Python 3.10 or newer
REM ---------------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 goto :no_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto :old_python
for /f "tokens=*" %%v in ('python --version') do echo  [ok] %%v

REM ---------------------------------------------------------------
REM  2. Node.js
REM ---------------------------------------------------------------
where npm >nul 2>nul
if errorlevel 1 goto :no_node
for /f "tokens=*" %%v in ('node --version') do echo  [ok] Node %%v

REM ---------------------------------------------------------------
REM  3. Config file
REM ---------------------------------------------------------------
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  [+] Created .env
)

REM ---------------------------------------------------------------
REM  4. Backend: virtual environment, packages, database
REM ---------------------------------------------------------------
echo.
echo  [1/3] Backend packages - first run takes a minute or two...
pushd backend
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :fail_venv
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail_pip

echo  [2/3] Database...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto :fail_db
popd

REM ---------------------------------------------------------------
REM  5. Frontend packages
REM ---------------------------------------------------------------
echo  [3/3] Frontend packages...
pushd frontend
if not exist "node_modules" (
    call npm install --no-audit --no-fund
    if errorlevel 1 goto :fail_npm
)
popd

REM ---------------------------------------------------------------
REM  6. Launch - each server in its own window
REM ---------------------------------------------------------------
echo.
echo  Starting backend  on http://localhost:8000
start "Travel Planner - Backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload"

echo  Starting frontend on http://localhost:5173
start "Travel Planner - Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

REM With TASK_BACKEND=celery in .env, jobs run on a Celery worker (needs Redis)
REM and Celery Beat sends the daily reminders. Inline mode needs neither.
findstr /r /b /c:"TASK_BACKEND=celery" ".env" >nul 2>nul
if not errorlevel 1 (
    echo  Starting Celery worker and beat  - TASK_BACKEND=celery, Redis must be running
    start "Travel Planner - Worker" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m celery -A app.tasks.celery_app worker --pool=solo --loglevel=info"
    start "Travel Planner - Beat" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m celery -A app.tasks.celery_app beat --loglevel=info"
)

echo.
echo  Opening your browser in a few seconds...
timeout /t 8 /nobreak >nul
start "" http://localhost:5173

echo.
echo  ==========================================
echo   Running. New windows opened for each
echo   server - keep them open while you use it.
echo   Emails print in the Backend window until
echo   SMTP is set in .env.
echo   Close them to stop it.
echo  ==========================================
echo.
pause
exit /b 0


REM ===============================================================
REM  Errors - each says what went wrong and what to do
REM ===============================================================
:no_python
echo  [X] Python was not found.
echo      Install Python 3.10+ from https://www.python.org/downloads/
echo      On the first installer screen, tick "Add python.exe to PATH".
echo      Then close this window and double-click start.bat again.
goto :end_fail

:old_python
echo  [X] Python 3.10 or newer is needed. You have:
python --version
echo      Install a newer one from https://www.python.org/downloads/
goto :end_fail

:no_node
echo  [X] Node.js was not found.
echo      Install the LTS version from https://nodejs.org/
echo      Then close this window and double-click start.bat again.
goto :end_fail

:fail_venv
echo  [X] Could not create the Python virtual environment.
popd
goto :end_fail

:fail_pip
echo  [X] Installing backend packages failed - see the error above.
popd
goto :end_fail

:fail_db
echo  [X] Setting up the database failed - see the error above.
popd
goto :end_fail

:fail_npm
echo  [X] Installing frontend packages failed - see the error above.
popd
goto :end_fail

:end_fail
echo.
echo  Copy the message above and send it over.
echo.
pause
exit /b 1
