@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if not exist build mkdir build
cl /nologo /std:c++17 /EHsc /O2 /fp:strict native\flymimic_rocket_replay.cpp /Fo:build\flymimic_rocket_replay.obj /Fe:build\flymimic_rocket_replay.exe
exit /b %errorlevel%
