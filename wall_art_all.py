import subprocess


# Call the pattern resizing script
subprocess.run(["python", "wall_art.py"])

# Make mockups
subprocess.run(["python", "wall_art_mocks.py"])
