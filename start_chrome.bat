@echo off
echo Closing any stuck Chrome automation processes...
taskkill /F /IM chrome.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting isolated Chrome with debugging enabled...
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9223 --user-data-dir="C:\Users\Isaiah\chrome_automation" --restore-last-session=false --no-default-browser-check --disable-crash-reporter --hide-crash-restore-bug --disable-infobars "https://www.linkedin.com"
