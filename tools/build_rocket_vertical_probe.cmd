@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict native\rocket_vertical_probe.cpp /Fo:build\rocket_vertical_probe.obj /Fe:build\rocket_vertical_probe.exe
exit /b %errorlevel%
