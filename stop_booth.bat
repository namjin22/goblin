@echo off
rem ============================================================
rem  Stops the Nongkkaebi server started by start_booth.bat
rem  (the restart loop and python main.py). Safe to run twice.
rem ============================================================
chcp 65001 >nul
powershell -NoProfile -Command "$me = $PID; Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $me -and ($_.CommandLine -like '*start_booth.bat*' -or $_.CommandLine -like '*main.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; 'stopped ' + $_.ProcessId }"
echo 농깨비 서버를 멈췄어요. (MODI 포트가 풀렸으니 hwtest.py 를 쓸 수 있어요)
