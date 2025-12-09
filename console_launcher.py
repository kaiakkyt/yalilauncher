# run launcher.pyw from here but catch the errors and print them to here
# mainly for debugging purposes
# do NOT use unless yk what ur doing

import subprocess
import sys
import os
from time import time

script_to_run = "launcher.pyw"

print(f"Using Python interpreter: {sys.executable}")
print(f"Attempting to launch {script_to_run}...")
print("" * 40)
print("-" * 40)
print("" * 40)

if not os.path.exists(script_to_run):
    print(f"Error: The file '{script_to_run}' was not found.")
    sys.exit(1)

try:
    subprocess.run(
        [sys.executable, script_to_run],
        check=True,
    )
    
    print(f"\n--- {script_to_run} finished successfully! ---")

except subprocess.CalledProcessError as e:
    print(f"\n--- {script_to_run} exited with failure status ---")
    print(f"Return Code: {e.returncode}")

except FileNotFoundError:
    print(f"\nError: The Python interpreter '{sys.executable}' was not found.")
    
except Exception as e:
    print(f"\n--- An unexpected system error occurred while launching the script: ---")
    print(f"Details: {e}")
