@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /EHsc /std:c++17 native\atomic_checkpoint_test.cpp /Fe:build\atomic_checkpoint_test.exe /Fo:build\atomic_checkpoint_test.obj
