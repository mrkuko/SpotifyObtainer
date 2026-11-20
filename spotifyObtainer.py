import hashlib
import os
import subprocess
import sys
import venv

# All paths are resolved relative to this file, not the current directory,
# so the script works no matter where it is launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(BASE_DIR, "requirements.txt")


# Determine the correct path based on the OS
def get_venv_bin(venv_dir: str, name: str):
    # Windows keeps executables in Scripts/, Unix-based systems
    # (Linux, macOS) in bin/
    folder = 'Scripts' if os.name == 'nt' else 'bin'
    return os.path.join(venv_dir, folder, name)


def get_venv_python(venv_dir: str):
    return get_venv_bin(venv_dir, 'python')


def get_venv_pip(venv_dir: str):
    return get_venv_bin(venv_dir, 'pip')


# Old versions (kept for reference), the OS check was duplicated:
# def get_venv_python(venv_dir: str):
#     if os.name == 'nt':  # Windows
#         return os.path.join(venv_dir, 'Scripts', 'python')
#     else:  # Unix-based (Linux, macOS)
#         return os.path.join(venv_dir, 'bin', 'python')
#
# def get_venv_pip(venv_dir: str):
#     if os.name == 'nt':  # Windows
#         return os.path.join(venv_dir, 'Scripts', 'pip')
#     else:  # Unix-based (Linux, macOS)
#         return os.path.join(venv_dir, 'bin', 'pip')


def create_venv(venv_dir: str):
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment in {venv_dir}", file=sys.stderr)
        venv.EnvBuilder(with_pip=True).create(venv_dir)


def requirements_hash() -> str:
    with open(REQUIREMENTS, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def install_packages(venv_dir: str):
    # Skip pip (and the network round-trip) unless the venv is new or
    # requirements.txt changed since the last successful install.
    stamp = os.path.join(venv_dir, ".requirements.sha256")
    current = requirements_hash()
    if os.path.exists(stamp):
        with open(stamp) as f:
            if f.read().strip() == current:
                return
    pip_path = get_venv_pip(venv_dir)
    # pip's output goes to stderr so stdout contains only the CSV
    subprocess.check_call([pip_path, "install", "-r", REQUIREMENTS],
                          stdout=sys.stderr)
    with open(stamp, "w") as f:
        f.write(current)


def run_python(venv_dir: str, py_script: str):
    python_path = get_venv_python(venv_dir)

    python_args = sys.argv[1:]
    # stdout/stderr/stdin are inherited: the CSV streams straight to stdout,
    # errors and login prompts stay visible, and the exit code is propagated.
    return subprocess.call([python_path, py_script] + python_args)

# def parse_flags():
#     args = sys.argv
#     if "-f" in args


def main():
    venv_dir = os.path.join(BASE_DIR, "venv")
    # Old: create_venv(venv_dir) ; install_packages(venv_dir)
    create_venv(venv_dir)
    install_packages(venv_dir)
    sys.exit(run_python(venv_dir, os.path.join(BASE_DIR, "generator.py")))


if __name__ == "__main__":
    main()
