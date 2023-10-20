@echo off
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

        @REM C:\CertFlash\file_transfer.py load %EXT% -f %FN% -p %FILE%
        set BIN=C:\CertFlash\file_transfer.exe load %FTYPE% -f %FN% -p %FILE%

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