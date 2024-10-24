import os,subprocess,sys,venv,sys

PACKAGES = ["spotipy", "python-dotenv"]
FLAGS: int = 0;

# Determine the correct path based on the OS
def get_venv_python(venv_dir: str):
    if os.name == 'nt':  # Windows
        return os.path.join(venv_dir, 'Scripts', 'python')
    else:  # Unix-based (Linux, macOS)
        return os.path.join(venv_dir, 'bin', 'python')

def get_venv_pip(venv_dir: str):
    if os.name == 'nt':  # Windows
        return os.path.join(venv_dir, 'Scripts', 'pip')
    else:  # Unix-based (Linux, macOS)
        return os.path.join(venv_dir, 'bin', 'pip')

def create_venv(venv_dir: str):
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment in {venv_dir}")
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    else:
        print("Virtual environment already exists.")

def install_packages(venv_dir: str):
    pip_path = get_venv_pip(venv_dir)
    subprocess.check_call([pip_path, "install"] + PACKAGES)

def run_python(venv_dir: str, py_script: str):
    python_path = get_venv_python(venv_dir)

    python_args = sys.argv[1:]
    result = subprocess.run([python_path, py_script] + python_args, capture_output=True, text=True)
    return result.stdout

# def parseFlags():
#     args = sys.argv
#     if "-f" in args

def main():
    

    venv_dir = os.path.join(os.getcwd(), "venv");
    packages = ["spotipy"]
    create_venv(venv_dir) ; install_packages(venv_dir)
    output = run_python(venv_dir, "generator.py")
    print(f"\n$BEGIN\n{output}$END\n")


if __name__ == "__main__":
    main()
