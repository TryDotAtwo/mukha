@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict /I data\reference\mujoco_3.9.0\include native\brain_body_probe.cpp /Fo:build\brain_body_probe.obj /Fe:build\brain_body_probe.exe /link build\fly_cuda64.lib data\reference\mujoco_3.9.0\lib\mujoco.lib
exit /b %errorlevel%
