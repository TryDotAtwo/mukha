@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
if not exist build mkdir build
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin\nvcc.exe" -std=c++17 -O2 -arch=sm_86 --fmad=false -DFF_FP64=1 --shared native\cuda_probe.cu -o build\fly_cuda64.dll -lcusparse
exit /b %errorlevel%
