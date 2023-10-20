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

REM Description:        Microchip Drag & Drop Utility
REM Date:               10/26/2023
REM VERSION:            1.1.0
REM
REM Revisions:
REM --------------------------------------------------------------------------
REM   11/10/2023    1.1.0   Updated to latest exe file name
REM   10/26/2023    1.0.0   Initial release

cls
SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
    :START
       if NOT "%9"=="" (
            echo.
            echo "Drag & Drop supports a maximum of 8 files for upload"
            echo.
            goto END
        )

        rem Parse parameter 1 into a path, filename & extension
            set PTH=%~d1%~p1
            set FN=%~n1
            set EXT=%~x1
            set FILE=%1

        if /I "%EXT%"==".crt" (
            set FTYPE=cert
        ) else if /I "%EXT%"==".pem" (
            set FTYPE=cert
        ) else if "%EXT%"==".key" (
            set FTYPE=key
        ) else (
            echo.
            echo "Drag & Drop 'file' invalid type (.pem, crt or .key only)
            echo.
            goto ERROR
        )

        set BIN=C:\CertFlash\file_upload.exe load %FTYPE% -f %FN% -p %FILE%
        @REM echo %BIN%
        call %BIN%

        @REM Shifts the input parameters i.e. %2 is shifted down to become %1
        shift
        if NOT "%1"=="" (
            goto START
        )

        :ERROR
            goto END
    :END
ENDLOCAL

timeout 10