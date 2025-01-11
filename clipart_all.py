import subprocess

# Call the pattern resizing script
subprocess.run(['python', 'clipart_resize.py'])

subprocess.run(['python', 'clipart.py'])

# Call zip.py to zip the resized pattern files
subprocess.run(['python', 'zip.py'])
