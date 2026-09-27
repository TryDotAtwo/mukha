@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
if not exist build mkdir build
cl /nologo /std:c++17 /EHsc /O2 /fp:strict /LD native\rocket_vertical_abi.cpp /Fo:build\rocket_vertical_checkpoint_abi.obj /Fe:build\rocket_vertical_checkpoint_abi.dll /link /OUT:build\rocket_vertical_checkpoint_abi.dll
exit /b %errorlevel%
