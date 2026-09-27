@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
for %%K in (transduction current adaptation) do (
  "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin\nvcc.exe" -std=c++17 -O2 -arch=sm_86 --fmad=false -c build\photoreceptor_author_%%K.cu -o build\photoreceptor_author_%%K.obj
  if errorlevel 1 exit /b 1
)
exit /b 0
