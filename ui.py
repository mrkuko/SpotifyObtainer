"""Graphical interface for Spotify Obtainer (CustomTkinter).

Start it with:  python spotifyObtainer.py --ui

It does the same as the command line: export Liked Songs or a playlist to
CSV, with podcast episodes going to a separate file. All the real work is
done by generator.py, this file only builds the window.
"""
import os
import queue
import re
import threading

import customtkinter as ctk

import dialogs
import generator
import textedit

LIKED = "Liked Songs"
PLAYLIST = "Playlist"

HINTS = {
    LIKED: "Exports every song you have liked. No link needed: you log in "
           "to Spotify in your browser on the first export.",
    PLAYLIST: "In Spotify, open the playlist, click \u22ef \u2192 Share "
              "\u2192 Copy link to playlist, and paste it here.",
}

# The Liked Songs page has its own address, which is not a playlist link.
# If someone pastes it into the playlist field, export Liked Songs instead.
LIKED_SONGS_LINK = re.compile(
    r"\s*(https?://open\.spotify\.com/(?:intl-[a-z-]+/)?collection/tracks"
    r"|spotify:(?:user:[^:]+:)?collection(?::tracks)?)\b.*")


def export_to_files(playlist, songs_path, episodes_path, log, sp=None):
    """Runs a whole export and writes the files. Returns (songs, episodes).

    playlist: link / URI / id, or None for Liked Songs.
    episodes_path: file for podcast episodes, or "" to skip them.
    log: function that receives progress messages (strings).
    sp: Spotify client; created with generator.create_client() if omitted.
    Kept free of any widgets so it can be tested without a window.
    """
    log("Connecting to Spotify (a browser window may open to log in)...")
    sp = sp or generator.create_client()
    log("Fetching your " + ("playlist..." if playlist else "Liked Songs..."))
    songs, episodes = generator.fetch_export(sp, playlist)

    with open(songs_path, "w", newline="", encoding="utf-8") as songs_file:
        generator.write_csv(songs_file, generator.TrackItem, songs)
    log(f"Wrote {len(songs)} songs to {songs_path}")

    if episodes and episodes_path:
        generator.write_episodes_file(episodes_path, episodes)
        log(f"Wrote {len(episodes)} episodes to {episodes_path}")
    elif episodes:
        log(f"Skipped {len(episodes)} episodes "
            "(choose an episodes file to export them)")
    return len(songs), len(episodes)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Spotify Obtainer {generator.__version__}")
        self.geometry("660x560")
        self.minsize(560, 480)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # The export runs in a thread; it talks to the window only through
        # this queue (tkinter widgets must be used from the main thread).
        self.messages = queue.Queue()

        form = ctk.CTkFrame(self)
        form.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Export to CSV",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8),
               sticky="w")

        self.source = ctk.CTkSegmentedButton(
            form, values=[LIKED, PLAYLIST], command=self.on_source_change)
        self.source.set(LIKED)
        self.source.grid(row=1, column=0, columnspan=2, padx=16, pady=8,
                         sticky="w")

        # One line explaining the selected mode; the text changes with it.
        self.hint = ctk.CTkLabel(
            form, text="", text_color=("gray40", "gray65"),
            justify="left", anchor="w", wraplength=580)
        self.hint.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 8),
                       sticky="w")

        # Playlist-only widgets are hidden (grid_remove) in Liked Songs mode
        # and shown again (grid) in Playlist mode, see on_source_change().
        self.playlist_entry = ctk.CTkEntry(
            form, placeholder_text="https://open.spotify.com/playlist/...")
        self.playlist_entry.grid(row=3, column=0, columnspan=2, padx=16,
                                 pady=8, sticky="ew")

        self.songs_row, self.songs_entry = self.file_row(
            form, 4, "Songs file",
            "Click Browse... to choose where to save", "songs.csv")
        self.episodes_row, self.episodes_entry = self.file_row(
            form, 5, "Episodes file (optional)",
            "No file: episodes are skipped", "episodes.csv",
            hint="Podcast episodes in the playlist are saved here. "
                 "Leave empty to skip them.")

        self.export_button = ctk.CTkButton(
            form, text="Export", command=self.on_export)
        self.export_button.grid(row=6, column=0, columnspan=2, padx=16,
                                pady=16, sticky="ew")

        self.log_box = ctk.CTkTextbox(self, state="disabled")
        self.log_box.grid(row=1, column=0, padx=16, pady=(8, 16),
                          sticky="nsew")

        # Ctrl+A, right-click menu, layout-independent Ctrl+C/V/X.
        # (_entry / _textbox are the plain tkinter widgets inside the
        # CustomTkinter ones; the key bindings must go on those.)
        for entry in (self.playlist_entry, self.songs_entry,
                      self.episodes_entry):
            textedit.add_editing(entry._entry)
        textedit.add_editing(self.log_box._textbox, read_only=True)

        self.dialog_open = False
        self.on_source_change(LIKED)

    def file_row(self, parent, row, label, placeholder, default_name,
                 hint=None):
        """Label (+ optional hint) + entry + Browse button, in one frame.

        Returns (frame, entry); the frame lets the whole row be hidden.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, padx=16, pady=(8, 4),
                   sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=label).grid(
            row=0, column=0, columnspan=2, sticky="w")
        if hint:
            ctk.CTkLabel(
                frame, text=hint, text_color=("gray40", "gray65"),
            ).grid(row=1, column=0, columnspan=2, sticky="w")
        entry = ctk.CTkEntry(frame, placeholder_text=placeholder)
        entry.grid(row=2, column=0, padx=(0, 8), pady=(4, 4), sticky="ew")
        ctk.CTkButton(
            frame, text="Browse...", width=90,
            command=lambda: self.browse(entry, label, default_name),
        ).grid(row=2, column=1, pady=(4, 4))
        return frame, entry

    def browse(self, entry, title, default_name):
        # Old version (kept for reference): always Tk's own dialog, which
        # looks out of place on Linux desktops.
        # path = tkinter.filedialog.asksaveasfilename(
        #     defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if self.dialog_open:
            return  # one dialog at a time
        initial = entry.get().strip() or os.path.join(
            os.path.expanduser("~"), default_name)

        def done(path):
            self.dialog_open = False
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)

        self.dialog_open = True
        dialogs.ask_save_path(self, title, initial, done)

    def on_source_change(self, value):
        # A playlist link is only needed for playlists, and only playlists
        # can contain episodes (Liked Songs cannot), so those widgets are
        # only shown in Playlist mode.
        # Old version (kept for reference): the widgets stayed visible but
        # greyed out, which suggested Liked Songs needed a link too.
        # state = "normal" if value == PLAYLIST else "disabled"
        # self.playlist_entry.configure(state=state)
        # self.episodes_entry.configure(state=state)
        self.hint.configure(text=HINTS[value])
        for widget in (self.playlist_entry, self.episodes_row):
            if value == PLAYLIST:
                widget.grid()  # restores the position from before
            else:
                widget.grid_remove()

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def on_export(self):
        playlist = None
        episodes_path = ""
        if self.source.get() == PLAYLIST:
            playlist = self.playlist_entry.get().strip()
            episodes_path = self.episodes_entry.get().strip()
            if not playlist:
                self.log("Error: paste a playlist link first.")
                return
            if LIKED_SONGS_LINK.fullmatch(playlist):
                self.log("That is the link to your Liked Songs, "
                         "switching to Liked Songs.")
                self.source.set(LIKED)
                self.on_source_change(LIKED)
                playlist = None
                episodes_path = ""
        songs_path = self.songs_entry.get().strip()
        if not songs_path:
            self.log("Error: choose where to save the songs file.")
            return

        self.export_button.configure(state="disabled", text="Working...")
        threading.Thread(
            target=self.worker,
            args=(playlist, songs_path, episodes_path),
            daemon=True,
        ).start()
        self.after(100, self.poll)

    def worker(self, playlist, songs_path, episodes_path):
        """Runs in a background thread."""
        def post(text):
            self.messages.put(("log", text))
        try:
            export_to_files(playlist, songs_path, episodes_path, post)
        except ValueError as error:
            self.messages.put(
                ("error", f"{error}\n{generator.PLAYLIST_HELP}"))
        except Exception as error:
            self.messages.put(("error", f"{type(error).__name__}: {error}"))
        self.messages.put(("done", ""))

    def poll(self):
        """Moves messages from the worker thread into the window."""
        try:
            while True:
                kind, text = self.messages.get_nowait()
                if kind == "log":
                    self.log(text)
                elif kind == "error":
                    self.log("Error: " + text)
                elif kind == "done":
                    self.export_button.configure(state="normal",
                                                 text="Export")
                    return
        except queue.Empty:
            pass
        self.after(100, self.poll)


def run():
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    App().mainloop()
