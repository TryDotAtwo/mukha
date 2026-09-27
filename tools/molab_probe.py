import marimo as mo
import marimo._code_mode as cm
import subprocess
import json
mo.status.toast('Fly CNS: native pairing connected')
async with cm.get_context() as ctx:
    print('CELLS', [(cell.id, str(cell.status)) for cell in ctx.cells])
print('GPU', subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout)
print('PROCESSES', subprocess.run(['ps','-eo','pid,comm'],capture_output=True,text=True,check=True).stdout)
print('CUDA', subprocess.run(['nvcc','--version'],capture_output=True,text=True,check=True).stdout)
help(cm)
