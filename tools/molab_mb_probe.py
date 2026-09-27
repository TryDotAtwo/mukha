import os
import shutil
import subprocess
import sys
import marimo as mo

mo.status.toast('MaleCNS synapse scan: paired')
for name in ('pyarrow', 'pandas', 'fsspec', 'requests'):
    try:
        module = __import__(name)
        print(name, getattr(module, '__version__', 'available'))
    except ImportError:
        print(name, 'missing')
print('python', sys.version.split()[0])
print('cwd', os.getcwd())
print('disk_free', shutil.disk_usage('/tmp').free)
processes = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True, text=True, check=True)
print('processes', '\n'.join(line for line in processes.stdout.splitlines()
                             if any(word in line for word in ('python', 'jupyter', 'marimo')))[-1500:])
