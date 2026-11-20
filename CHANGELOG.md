# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versions follow [Semantic Versioning](https://semver.org/). While the major
version is 0, a minor bump (`0.x.0`) may contain breaking changes.

## [Unreleased]

### Breaking changes

- **CSV columns changed.** The songs file now starts with readable columns
  (`name`, `artist_names`, `album_name`, `added_at`, `duration`, `url`),
  followed by simple values and, last, the raw JSON columns. The episodes
  file got the same treatment (`name`, `show_name`, `release_date`, ...).
  Anything that read columns by position needs updating.
- `available_markets` is no longer exported (neither as a column nor inside
  the `album` JSON). Together with the new order this makes the songs file
  about half the size.

### Added

- README rewritten as a step-by-step guide (Spotify app, `.env`, first login,
  window and command line, CSV columns, troubleshooting) with screenshots in
  `docs/images/`, and a `.env.example` template.
- Graphical interface (CustomTkinter): `python spotifyObtainer.py --ui`.
  Same features as the command line: Liked Songs or a playlist, a songs
  file and an optional separate episodes file. Only the options that fit
  the chosen mode are shown, with a hint for each, and a pasted link to the
  Liked Songs page is understood.
- Browse buttons open the desktop's native save dialog (`kdialog` on KDE,
  `zenity` elsewhere on Linux; Windows and macOS already use theirs).
- Text fields: Ctrl+A selects all, a right-click menu (cut / copy / paste /
  select all), Ctrl+A/C/V/X on any keyboard layout, and the log can be
  selected and copied.
- `export_to_files()` in `ui.py`, built on the refactored `create_client()`,
  `fetch_export()` and `write_episodes_file()` in `generator.py`.

## [0.3.0] - 2026-11-20

Big cleanup release after a long pause. **The output format changed**, so
anything that parsed the old output needs updating.

### Breaking changes

- The `$BEGIN` / `$END` markers are gone. stdout is now only the CSV.
- Column order is now fixed (it was random on every run). Two new last
  columns, `linked_from` and `restrictions`, were added.
- Nested fields (`album`, `artists`, `external_urls`, ...) are written as
  JSON instead of Python repr.
- Podcast episodes are no longer mixed into the songs CSV.
- Errors are no longer swallowed: the exit code is non-zero on failure and
  progress / pip output goes to stderr.
- The playlist argument is validated: anything that is not a playlist id,
  `spotify:playlist:` URI or open.spotify.com playlist link exits with code 2.
- Arguments are parsed with argparse (unknown flags are errors).

### Added

- `--episodes-out FILE` writes podcast episodes found in a playlist to their
  own CSV file; without it they are skipped with a note on stderr.
- `--version` flag.
- `EpisodeItem` schema; `TrackItem` now covers `linked_from`, `restrictions`
  and a nullable `preview_url`.
- This changelog.

### Changed

- Venv, `.env`, `generator.py` and the token cache are resolved relative to
  the script, so it works from any directory.
- pip only runs when the venv is new or `requirements.txt` changed.
- Dependencies are read from `requirements.txt` (no duplicate list).
- Function names are snake_case (`get_all_tracks`, `get_playlist_tracks`);
  duplicated pagination and OS-check code was shared; code passes flake8.
- README: example playlist replaced (Spotify-owned playlists are not
  available to new apps), new limitations and usage sections.
- `.gitignore`: ignores all `*.csv`, no longer ignores `README*`.

### Fixed

- stdout was closed after writing the CSV.
- CSV had blank lines between rows on Windows.

## [0.2.0] - 2026-08-08

### Added

- Export any playlist by link, `spotify:playlist:` URI or id (public, private
  and collaborative), with the matching Spotify scopes.
- `requirements.txt`.

### Changed

- README rewritten (Spotify app setup, `.env`, usage).

## [0.1.0] - 2024-10-24

First version.

### Added

- Export of the user's Liked Songs as CSV.
- `spotifyObtainer.py` sets up a local venv and installs dependencies;
  `generator.py` talks to the Spotify API (via spotipy).
- README and LICENSE.

[0.3.0]: https://github.com/mrkuko/SpotifyObtainer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mrkuko/SpotifyObtainer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mrkuko/SpotifyObtainer/releases/tag/v0.1.0
