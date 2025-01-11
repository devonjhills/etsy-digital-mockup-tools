import subprocess

# Call the pattern resizing script
subprocess.run(['python', 'pattern_resize.py'])

subprocess.run(['python', 'pattern.py'])

# Call zip.py to zip the resized pattern files
subprocess.run(['python', 'zip.py'])
