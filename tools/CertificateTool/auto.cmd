@echo off
REM © 2023 Microchip Technology Inc. and its subsidiaries
REM Subject to your compliance with these terms, you may use this Microchip software
REM and any derivatives exclusively with Microchip products. You are responsible for 
REM complying with third party license terms applicable to your use of third party 
REM software (including open source software) that may accompany this Microchip 
REM software.
REM Redistribution of this Microchip software in source or binary form is allowed and
REM must include the above terms of use and the following disclaimer with the 
REM distribution and accompanying materials.
REM SOFTWARE IS “AS IS.” NO WARRANTIES, WHETHER EXPRESS, IMPLIED OR STATUTORY, APPLY 
REM TO THIS SOFTWARE, INCLUDING ANY IMPLIED WARRANTIES OF NON-INFRINGEMENT, 
REM MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT WILL MICROCHIP BE
REM LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE, INCIDENTAL OR CONSEQUENTIAL LOSS, 
REM DAMAGE, COST OR EXPENSE OF ANY KIND WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER 
REM CAUSED, EVEN IF MICROCHIP HAS BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE 
REM FORESEEABLE. TO THE FULLEST EXTENT ALLOWED BY LAW, MICROCHIP’S TOTAL LIABILITY ON 
REM ALL CLAIMS RELATED TO THE SOFTWARE WILL NOT EXCEED AMOUNT OF FEES, IF ANY, YOU 
REM PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.

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