@echo off
REM Build script for SenseGlove Bridge (MSVC x64)
REM Requires Visual Studio 2022 with C++ workload

setlocal

REM Find Visual Studio installation
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "tokens=*" %%i in ('%VSWHERE% -latest -property installationPath') do set VSINSTALL=%%i

if "%VSINSTALL%"=="" (
    echo ERROR: Visual Studio not found!
    exit /b 1
)

echo Found Visual Studio at: %VSINSTALL%

REM Set up MSVC x64 environment
call "%VSINSTALL%\VC\Auxiliary\Build\vcvarsall.bat" x64

REM Paths
set SCRIPT_DIR=%~dp0
set API_DIR=%SCRIPT_DIR%..\SenseGlove-API
set INCLUDE_DIR=%API_DIR%\include
set LIB_DIR=%API_DIR%\lib\win64\msvc143\release
set OUTPUT_DIR=%SCRIPT_DIR%bin

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo.
echo Building SenseGlove Bridge...
echo   Include: %INCLUDE_DIR%
echo   Lib:     %LIB_DIR%
echo   Output:  %OUTPUT_DIR%
echo.

cl.exe /nologo /EHsc /std:c++17 /MD /O2 ^
    /I"%INCLUDE_DIR%" ^
    "%SCRIPT_DIR%senseglove_bridge.cpp" ^
    /Fe:"%OUTPUT_DIR%\senseglove_bridge.exe" ^
    /link /LIBPATH:"%LIB_DIR%" sgcore.lib sgconnect.lib legacy_stdio_definitions.lib

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BUILD FAILED!
    exit /b 1
)

REM Copy DLLs to output directory
echo.
echo Copying DLLs...
copy /Y "%LIB_DIR%\sgcore.dll" "%OUTPUT_DIR%\" >nul
copy /Y "%LIB_DIR%\sgconnect.dll" "%OUTPUT_DIR%\" >nul

REM Clean up intermediate files
del /Q "%SCRIPT_DIR%senseglove_bridge.obj" 2>nul

echo.
echo BUILD SUCCESSFUL!
echo Executable: %OUTPUT_DIR%\senseglove_bridge.exe
echo.

endlocal
