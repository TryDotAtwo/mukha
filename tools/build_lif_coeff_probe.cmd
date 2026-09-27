@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if not exist build mkdir build
cl /nologo /std:c++17 /O2 /EHsc /I native native\lif_coeff_probe.cpp /Fe:build\lif_coeff_probe.exe
exit /b %errorlevel%
