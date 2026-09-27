@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict native\visual_calibration_probe.cpp /Fo:build\visual_calibration_probe.obj /Fe:build\visual_calibration_probe.exe
exit /b %errorlevel%
