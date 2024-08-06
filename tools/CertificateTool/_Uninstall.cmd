@echo off
echo.
echo.
echo PIP List (Current)
echo ------------------
call pip list
echo.
echo Removing modules...
echo -------------------
type requirements.txt
echo.
call pip uninstall -y -r requirements.txt >nul
echo PIP List (Now)
call pip list

pause