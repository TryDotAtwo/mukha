@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict /LD native\huang.cpp /Fo:build\huang.obj /Fe:build\huang_reference.dll
exit /b %errorlevel%
