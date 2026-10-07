@echo off
rem ============================================================
rem  Nongkkaebi booth launcher (Windows)
rem  - starts main.py, restarts it automatically if it dies
rem  - opens the web UI fullscreen in Edge
rem  Edit the settings below, then double-click this file.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Nongkkaebi booth

rem ---- settings ------------------------------------------------
rem webcam index (check with: python hwtest.py / README "camera" section)
set CAM=1
rem extra options, e.g.  --mock   --no-auto   --verify-vent   (can also be set from outside)
rem (if not set, it stays empty)
rem port of the web UI
set PORT=5000
rem 1 = open Edge fullscreen after start, 0 = server only (can also be set from outside)
if not defined OPEN_BROWSER set OPEN_BROWSER=1
rem --------------------------------------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo [!] python 을 찾을 수 없어요. Python 설치와 PATH 를 확인해 주세요.
  pause
  exit /b 1
)

if not exist "web\dist\index.html" (
  echo [!] web\dist 가 없어요. 웹 UI 가 빌드되지 않았어요. 예전 화면^(/legacy 와 같은^)으로 열려요.
  echo     web 폴더에서  npm install  그리고  npm run build  를 실행하세요.
  echo.
)

echo 농깨비를 시작해요. 8초 뒤 브라우저가 전체화면으로 열려요.
echo 끝내려면 이 창에서 Ctrl+C 를 누르고 N 이 아니라 Y 를 입력하세요.
echo.

rem open the browser once, a few seconds after the server starts
if "%OPEN_BROWSER%"=="1" start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 8; try { Start-Process msedge -ArgumentList '--app=http://localhost:%PORT%/','--start-fullscreen' -ErrorAction Stop } catch { Start-Process 'http://localhost:%PORT%/' }"

:run
python main.py --cam %CAM% --port %PORT% %EXTRA_ARGS%
echo.
echo [!] 농깨비가 멈췄어요 ^(코드 %errorlevel%^). 3초 뒤 다시 시작해요.
echo     환기창이 맞는지 화면의 [운영자]에서 확인해 주세요.
rem ping waits ~3s and also works when started detached (timeout does not)
ping -n 4 127.0.0.1 >nul
goto run
