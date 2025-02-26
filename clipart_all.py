import subprocess
import sys

# Check for an optional max_size parameter passed to clipart_all.py
max_size = None
if len(sys.argv) > 1:
    try:
        max_size = int(sys.argv[1])
    except ValueError:
        pass

# Build the command for clipart_resize.py with an optional --max_size argument.
clipart_resize_cmd = ['python', 'clipart_resize.py']
if max_size is not None:
    clipart_resize_cmd.extend(['--max_size', str(max_size)])
subprocess.run(clipart_resize_cmd)

subprocess.run(['python', 'clipart.py'])
subprocess.run(['python', 'zip.py'])
