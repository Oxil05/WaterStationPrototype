import os
import subprocess
import sys
import shutil

def build():
    print("Preparing to build stand-alone executable for AquaFlow Desktop...")
    
    # Locate project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    app_script = os.path.join(project_root, "desktop_app.py")
    
    # Check if desktop_app.py exists
    if not os.path.exists(app_script):
        print(f"Error: {app_script} not found!")
        sys.exit(1)
        
    print(f"Target Script: {app_script}")
    
    # Check if PyInstaller is installed in active environment
    try:
        import PyInstaller
        print("PyInstaller detected.")
    except ImportError:
        print("PyInstaller is not installed in the active environment. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    # Command arguments for PyInstaller
    # --onefile: bundle into a single executable
    # --noconsole: do not open a command window
    # --collect-all customtkinter: copy all assets for customtkinter library
    # --clean: clean cache before building
    args = [
        "desktop_app.py",
        "--onefile",
        "--noconsole",
        "--clean",
        "--collect-all", "customtkinter",
        "--name", "AquaFlow_POS"
    ]
    
    print(f"Running PyInstaller with arguments: {args}")
    
    import PyInstaller.__main__
    PyInstaller.__main__.run(args)
    
    print("\n-------------------------------------------")
    print("Build complete!")
    print("The executable has been saved in the 'dist' directory:")
    dist_dir = os.path.join(project_root, "dist")
    print(f"Target location: {dist_dir}\\AquaFlow_POS.exe")
    print("-------------------------------------------")

if __name__ == "__main__":
    build()
