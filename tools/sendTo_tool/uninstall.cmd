@echo off
REM Description:        Microchip Firmware DFU Utility Un-Installer
REM Date:               05/23/2023
REM Author:             C75117
REM VERSION:            1.0.0
REM
REM Revisions:
REM --------------------------------------------------------------------------
REM   05/23/2023    1.0.0   Initial release


SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
    call install -u
ENDLOCAL
