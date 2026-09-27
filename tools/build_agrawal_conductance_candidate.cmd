@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
if not exist build mkdir build
cl /nologo /std:c++17 /O2 /EHsc /Febuild\agrawal_conductance_candidate.exe native\agrawal_conductance_candidate.cpp
exit /b %errorlevel%
