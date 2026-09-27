@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /EHsc /std:c++17 native\photon_abi_probe.cpp build\fly_photon.lib /Fe:build\photon_abi_probe.exe /Fo:build\photon_abi_probe.obj
exit /b %errorlevel%
