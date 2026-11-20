# Spotify Obtainer

A small script that uses the official [Spotify Web API](https://developer.spotify.com/documentation/web-api) (via [spotipy](https://spotipy.readthedocs.io/)) to export track metadata to CSV. It can export either:
- your **Liked Songs** (saved tracks library), or
- **any playlist you can access**, by pasting its Spotify link (public, private or collaborative, as long as your account has access to it).

> ⚠️ This tool only exports track **metadata** (title, artist, album, id, uri, duration, ...) to a CSV file — it does **not** download audio. Spotify's API does not provide audio files, and downloading streamed audio would violate Spotify's Terms of Service.

The script:
- creates a local `venv` virtual environment inside the repo folder,
- installs its dependencies (`spotipy`, `python-dotenv`) into it,
- authenticates with your Spotify account,
- prints the resulting CSV to stdout (progress messages and errors go to stderr).

## Requirements

- Python 3.11+ (uses modern typing features)
- A Spotify account
- A Spotify Developer app (free, see below)

## 1. Create a Spotify Developer app

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app**.
3. Fill in a name/description, select **Web API** when asked which APIs you're using.
4. Add a **Redirect URI**. As of Spotify's [2025 security update](https://developer.spotify.com/blog/2025-02-12-increasing-the-security-requirements-for-integrating-with-spotify), `localhost` is **no longer accepted**. Use one of:
   - `http://127.0.0.1:8888/callback` (loopback address, HTTP is allowed here), or
   - an `https://...` URL you control.
5. Save the app, then open **Settings** to copy the **Client ID** and **Client secret**.

## 2. Configure environment variables

Create a `.env` file in the repo root:

```sh
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

The redirect URI must exactly match the one registered in the dashboard.

## 3. Set up the environment

You can either let the script set itself up automatically, or do it manually.

### Option A: automatic (recommended)

Just run [spotifyObtainer.py](spotifyObtainer.py) (see below) — on first run it creates a `venv` folder and installs the dependencies for you.

### Option B: manual

```sh
python -m venv venv
```

Activate it:

```sh
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate
```

Then install dependencies:

```sh
pip install -r requirements.txt
```

## 4. Run it

The first run of [spotifyObtainer.py](spotifyObtainer.py) will:
- create the `venv` folder (`python -m venv venv`) and install dependencies, if not already done,
- open a browser window asking you to log in and authorize the app (a one-time step; spotipy caches the token in a local `.cache` file afterwards).

### Export your Liked Songs

```sh
python spotifyObtainer.py
```

If you set up the venv manually (Option B), you can instead run [generator.py](generator.py) directly inside the activated venv:

```sh
python generator.py
```

### Export a specific playlist by link

Pass the playlist link (or `spotify:playlist:<id>` URI, or bare playlist id) as an argument:

```sh
python spotifyObtainer.py https://open.spotify.com/playlist/<your_playlist_id>
```

This works for playlists you own, playlists you follow, private playlists and collaborative playlists — as long as the logged-in account has access to them. Use a playlist created by a user; Spotify-owned playlists are not available to new apps (see below).

### Graphical interface

```sh
python spotifyObtainer.py --ui
```

Opens a window (built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)) that does the same as the command line: choose **Liked Songs** or paste a **playlist** link, pick where to save the songs file and, for playlists, an optional separate file for podcast episodes, then click **Export**. The first export opens a browser window for the Spotify login, just like the command line. The **Browse...** buttons open your desktop's own save dialog (on Linux this uses `kdialog` on KDE or `zenity` elsewhere, if installed; otherwise Tk's built-in dialog). It needs tkinter, which comes with most Python installs (on some Linux distributions it is a separate package, for example `python3-tk`).

### Playlists that contain podcast episodes

Playlists can mix songs and podcast episodes. Episodes have different fields than songs, so they never go into the songs CSV. Pass `--episodes-out` to write them to their own file:

```sh
python spotifyObtainer.py https://open.spotify.com/playlist/<your_playlist_id> --episodes-out episodes.csv > songs.csv
```

Without `--episodes-out`, episodes are skipped and a message like `skipped 3 episodes (use --episodes-out FILE to export them)` is printed to stderr. Your Liked Songs cannot contain episodes, so the flag has no effect there (no file is created).

## Output

The CSV (`;`-delimited) is printed to stdout. Setup messages, pip output and errors go to stderr, so stdout is always a clean CSV:

```
added_at;album;artists;...;uri
2024-01-01T12:00:00Z;{...};[...];...;spotify:track:...
```

Redirect stdout to a file if you want to save it, e.g.:

```sh
python spotifyObtainer.py > liked_songs.csv
```

The exit code is non-zero if the export fails.

The songs file starts with readable columns, so you can open it in a spreadsheet or text editor and see your music right away:

| Column | Example |
|---|---|
| `name` | `DEVOLUTION` |
| `artist_names` | `STARSET` (several artists: `A, B`) |
| `album_name` | `HORIZONS` |
| `added_at` | `2026-10-13T07:27:24Z` |
| `duration` | `5:09` |
| `url` | `https://open.spotify.com/track/...` |

After these come simple values (`id`, `uri`, `popularity`, `explicit`, `duration_ms`, ...) and, at the end, the raw data as JSON inside the cell (`album`, `artists`, `external_ids`, `external_urls`). `linked_from` and `restrictions` are only filled when Spotify returns them. `available_markets` (a list of around 180 countries per song) is not exported.

The episodes file follows the same idea: `name`, `show_name`, `release_date`, `added_at`, `duration`, `url`, then the details (`description`, `language`, ...) and the raw JSON (`show`, `images`, ...).

## Notes / limitations

- Requires the `user-library-read`, `playlist-read-private` and `playlist-read-collaborative` scopes, requested automatically on first login.
- Pagination is handled automatically, so libraries/playlists larger than one API page (50–100 items) are fully exported.
- Podcast episodes inside playlists go to a separate CSV, see `--episodes-out` above.
- Local files added to your library/playlists (not available on Spotify's catalog) are skipped, since Spotify doesn't return track metadata for them.
- **Spotify-owned playlists are not available.** Since Spotify's [November 2024 Web API changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), apps created after that date (and apps in development mode) get a `404` when requesting Spotify-owned editorial and algorithmic playlists, such as "Today's Top Hits", "Discover Weekly" or "Daily Mix". Playlists created by users work normally. As a workaround, copy the playlist into one of your own and export that.
- For the same reason, `preview_url` is empty (`null`) for new apps.
