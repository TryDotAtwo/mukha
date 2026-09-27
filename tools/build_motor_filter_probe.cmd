@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict native\motor_filter_probe.cpp /Fo:build\motor_filter_probe.obj /Fe:build\motor_filter_probe.exe
if errorlevel 1 exit /b 1
build\motor_filter_probe.exe
exit /b %errorlevel%
