@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /fp:strict native\dallmann_observation_cli.cpp /Fo:build\dallmann_observation_cli.obj /Fe:build\dallmann_observation_cli.exe
exit /b %errorlevel%
