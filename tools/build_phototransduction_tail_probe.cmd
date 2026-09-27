@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin\nvcc.exe" -std=c++17 -O2 -lineinfo -DFF_SAFE_TRANSDUCTION=1 -DFF_ENTITY_RNG=1 -DFF_MICROVILLI=30001 -arch=sm_86 --fmad=false native\phototransduction_probe.cu -o build\phototransduction_tail_probe.exe
exit /b %errorlevel%
