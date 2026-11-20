"""Native "Save as" dialog: the desktop's own dialog instead of Tk's.

- Linux: kdialog (KDE) or zenity (GNOME and others), whichever fits the
  desktop and is installed. Falls back to Tk's dialog if neither is.
- Windows and macOS: Tk's dialog already *is* the native system dialog
  there, so it is used as-is.
"""
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter.filedialog


def native_save_command(title: str, initial_path: str):
    """Command line for the desktop's save dialog, or None to use Tk's."""
    if not sys.platform.startswith("linux"):
        return None  # Windows / macOS: Tk already shows the native dialog
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    tools = ["kdialog", "zenity"] if "KDE" in desktop else [
        "zenity", "kdialog"]
    for tool in tools:
        if not shutil.which(tool):
            continue
        if tool == "kdialog":
            return ["kdialog", "--title", title, "--getsavefilename",
                    initial_path, "CSV files (*.csv)"]
        return ["zenity", "--file-selection", "--save",
                f"--title={title}", f"--filename={initial_path}",
                "--file-filter=CSV files | *.csv",
                "--file-filter=All files | *"]
    return None


def ensure_csv(path: str) -> str:
    """Adds .csv when the user typed a name without an extension."""
    return path if os.path.splitext(path)[1] else path + ".csv"


def tk_save_dialog(window, title: str, initial_path: str) -> str:
    folder, name = os.path.split(initial_path)
    path = tkinter.filedialog.asksaveasfilename(
        parent=window, title=title, initialdir=folder or None,
        initialfile=name, defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*")])
    return path or ""  # Tk returns "" or () when cancelled


def ask_save_path(window, title: str, initial_path: str, on_done):
    """Shows a save dialog and calls on_done(path) on the Tk main thread.

    path is "" when the user cancels. The external dialog runs in a thread
    so the main window keeps responding (and is not marked as frozen by
    the desktop) while the dialog is open.
    """
    command = native_save_command(title, initial_path)
    if command is None:
        on_done(tk_save_dialog(window, title, initial_path))
        return

    results = queue.Queue()

    def run():
        try:
            results.put(subprocess.run(command, capture_output=True,
                                       text=True))
        except OSError as error:
            results.put(error)

    def poll():
        try:
            result = results.get_nowait()
        except queue.Empty:
            window.after(100, poll)
            return
        # kdialog / zenity: 0 = file chosen, 1 = cancelled, else an error.
        if isinstance(result, OSError) or result.returncode not in (0, 1):
            on_done(tk_save_dialog(window, title, initial_path))
        elif result.returncode == 0 and result.stdout.strip():
            on_done(ensure_csv(result.stdout.strip()))
        else:
            on_done("")

    threading.Thread(target=run, daemon=True).start()
    window.after(100, poll)
