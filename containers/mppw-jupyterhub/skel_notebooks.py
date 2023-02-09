import pkginfo
import glob
import shutil
import importlib
import os

def main():
    for wheel in [pkginfo.Wheel(f) for f in glob.glob('dist/*.whl')]:
        mod_name = wheel.name.replace('-', '_')
        mod = importlib.import_module(mod_name)
        mod_notebook_dir = os.path.join(os.path.dirname(mod.__file__), "notebooks")
        skel_notebook_dir = os.path.join("/etc/skel/notebooks", mod_name)
        print(f"Copying module notebooks from {mod_notebook_dir} to {skel_notebook_dir}...")
        shutil.copytree(mod_notebook_dir, skel_notebook_dir)

if __name__ == "__main__":
    main()