import subprocess

# Create seamless grid
# subprocess.run(['python', 'seamless.py'])

# Call the pattern resizing script
subprocess.run(['python', 'pattern_resize.py'])

# Make mockups
subprocess.run(['python', 'pattern.py'])

# Call zip.py to zip the resized pattern files
subprocess.run(['python', 'zip.py'])
