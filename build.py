# if you guys want to compile this yourselves, here's how
# yea pretty cool console build script right?

import os
import shutil
import time
import PyInstaller.__main__

os.environ['PYGAME_HIDE_SUPPORT_INFO'] = '1'

version = input("Set version name... (e.g., 1.01.25) ")

print("Cleaning previous builds...")
time.sleep(1)

if os.path.isdir("dist"):
    shutil.rmtree("dist", ignore_errors=True)
if os.path.isdir("build"):
    shutil.rmtree("build", ignore_errors=True)
if os.path.isdir("__pycache__"):
    shutil.rmtree("__pycache__", ignore_errors=True)
spec_file = f"YaliLauncher.spec"
if os.path.isfile(spec_file):
    os.remove(spec_file)
error_file = "error_log.txt"
if os.path.isfile(error_file):
    os.remove(error_file)

input("Press enter to build...")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
launcher_path = os.path.join(project_root, 'launcher.pyw')

sep = os.pathsep

exclude = {'dist', 'build', '__pycache__', '.git', '.idea', 'venv', '.venv', '.build'}

add_data_args = []
for entry in sorted(os.listdir(project_root)):
    if entry in exclude:
        continue
    full = os.path.join(project_root, entry)
    if os.path.isdir(full) or os.path.isfile(full):
        dest = entry
        add_data_args.append(f"--add-data={full}{sep}{dest}")

py_args = [launcher_path, '--windowed']
icon_path = os.path.join(project_root, 'components', 'icon', 'icon.ico')
if os.path.exists(icon_path):
    py_args.append(f"--icon={icon_path}")

py_args.extend(add_data_args)
py_args.extend(['--log-level=WARN', '--clean', '--name=YaliLauncher'])

print('Running PyInstaller with the following args:')
for a in py_args:
    print('  ', a)

errfile = os.path.join(script_dir, 'error_log.txt')
try:
    PyInstaller.__main__.run(py_args)
    print(f"Build complete. Exported .exe for YaliLauncher v{version}!")
except Exception as e:
    print('PyInstaller failed:', e)
    try:
        with open(errfile, 'w', encoding='utf-8') as ef:
            ef.write(str(e))
    except Exception:
        pass