@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /I data\reference\mujoco_3.9.0\include native\body_motor_probe.cpp /Fo:build\body_motor_probe.obj /Fe:build\body_motor_probe.exe /link data\reference\mujoco_3.9.0\lib\mujoco.lib
exit /b %errorlevel%
