import subprocess
import sys
import argparse

# Create an argument parser
parser = argparse.ArgumentParser(description='Run clipart scripts.')
parser.add_argument('-s', action='store_true', help='Run strokes.py instead of clipart.py')
parser.add_argument('-m', '--max_size', type=int, default=None, help='Maximum size for clipart_resize.py (optional)')

# Parse the arguments
args = parser.parse_args()

# Build the command for clipart_resize.py with an optional --max_size argument.
clipart_resize_cmd = ['python', 'clipart_resize.py']
if args.max_size is not None:
    clipart_resize_cmd.extend(['--max_size', str(args.max_size)])
subprocess.run(clipart_resize_cmd)

if args.s:
    subprocess.run(['python', 'strokes.py'])
else:
    subprocess.run(['python', 'clipart.py'])

subprocess.run(['python', 'zip.py'])
