@echo off
REM Description:        Microchip Auto Certificate Launcher
REM Date:               09/13/2023
REM VERSION:            1.0.0
REM
REM Revisions:
REM --------------------------------------------------------------------------
REM   09/13/2023    1.0.0   Initial release

SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
    set GIT_PATH="%PROGRAMFILES%\Git\bin\sh.exe"
    set BASH_SCRIPT="./ac.sh"
    cls
    if exist %GIT_PATH% (
       %GIT_PATH% --login -i -c %BASH_SCRIPT%
    ) else (
        echo.
        echo.
        echo Git was not found at %GIT_PATH%
        echo       Is Git installed?
        echo.
        echo Please manually launch the shell
        echo    and execute 'sh ./ac.sh'
        echo. 
    )
ENDLOCAL
echo.
echo.&echo Press any key to exit...
pause > nul