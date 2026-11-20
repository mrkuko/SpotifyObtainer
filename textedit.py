"""Editing support for text fields that Tk is missing on Linux.

- Ctrl+A selects all (Tk's default on Linux moves to the line start).
- A right-click menu: Cut / Copy / Paste / Select All.
- Ctrl+A/C/V/X also work when the keyboard layout gives a non-Latin
  letter for the key (Tk only reacts to the Latin letter).
- Read-only boxes (the log) can be focused, selected and copied.
"""
import sys
import tkinter

# Physical key codes of A, C, V and X. Used when the key's letter is not
# a plain Latin one, so the shortcuts work with any keyboard layout.
if sys.platform.startswith("linux"):
    LETTER_BY_KEYCODE = {38: "a", 54: "c", 55: "v", 53: "x"}  # X11
elif sys.platform == "win32":
    LETTER_BY_KEYCODE = {65: "a", 67: "c", 86: "v", 88: "x"}  # VK codes
else:
    LETTER_BY_KEYCODE = {}  # macOS uses Command, handled by Tk itself


def shortcut_letter(event):
    if len(event.keysym) == 1 and event.keysym.isascii():
        return event.keysym.lower()
    return LETTER_BY_KEYCODE.get(event.keycode)


def select_all(widget):
    if isinstance(widget, tkinter.Text):
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "end-1c")
    else:
        widget.select_range(0, "end")
        widget.icursor("end")


def add_editing(widget, read_only=False):
    """Adds the shortcuts and menu to a plain tkinter Entry or Text."""
    actions = {"c": "<<Copy>>"}
    if not read_only:
        actions |= {"v": "<<Paste>>", "x": "<<Cut>>"}

    def on_ctrl_key(event):
        letter = shortcut_letter(event)
        if letter == "a":
            select_all(widget)
            return "break"
        if letter in actions:
            widget.event_generate(actions[letter])
            # "break" stops Tk's own binding, so nothing happens twice
            return "break"
        return None  # other shortcuts (Ctrl+Left, ...) keep working

    menu = tkinter.Menu(widget, tearoff=0)
    if not read_only:
        menu.add_command(label="Cut",
                         command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy",
                     command=lambda: widget.event_generate("<<Copy>>"))
    if not read_only:
        menu.add_command(label="Paste",
                         command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=lambda: select_all(widget))

    def show_menu(event):
        widget.focus_set()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    if sys.platform != "darwin":
        widget.bind("<Control-KeyPress>", on_ctrl_key)
    widget.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>",
                show_menu)
    if read_only:
        # Tk does not focus a disabled Text on click, so Ctrl+C / Ctrl+A
        # would go nowhere. Focus it explicitly.
        widget.bind("<Button-1>", lambda event: widget.focus_set(),
                    add="+")
