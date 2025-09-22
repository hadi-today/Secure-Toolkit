import os
import subprocess
import sys

VENV_DIR = "venv"
REQUIREMENTS_FILE = "requirements.txt"
MAIN_SCRIPT = "main.py"

def get_python_executable():
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def venv_exists():
    return os.path.isdir(VENV_DIR)

def create_venv():
    if not venv_exists():
        print("Virtual environment not found. Creating...")
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
            print(f"Virtual environment created successfully in '{VENV_DIR}'.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1) 
    else:
        print("Virtual environment already exists.")

def install_requirements():
    python_executable = get_python_executable()
    
    if not os.path.exists(python_executable):
        print(f"Python executable not found at '{python_executable}'. Please ensure the virtual environment is set up correctly.")
        sys.exit(1)

    print("Checking and installing requirements...")
    try:
        subprocess.run(
            [python_executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
            check=True
        )
        print("Requirements installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)

def run_main_script():
    python_executable = get_python_executable()
    
    print(f"Running the main program: {MAIN_SCRIPT}...")
    try:
        subprocess.run([python_executable, MAIN_SCRIPT], check=True)
    except FileNotFoundError:
        print(f"Error: Main program file '{MAIN_SCRIPT}' not found.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"The program stopped with an error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_venv()
    
    install_requirements()
    
    run_main_script()