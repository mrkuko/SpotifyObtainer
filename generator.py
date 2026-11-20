import argparse
import csv
import json
import os
import re
import sys
from typing import Any, NotRequired, TypedDict

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


# .env and the spotipy token cache live next to this file, not in the cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Old version (kept for reference), before linked_from / restrictions were
# added and before preview_url could be null:
# class TrackItem(TypedDict):
#     album: dict
#     artists: list
#     available_markets: list
#     disc_number: int
#     duration_ms: int
#     explicit: bool
#     external_ids: dict
#     external_urls: dict
#     href: str
#     id: str
#     is_local: bool
#     is_playable: bool
#     name: str
#     popularity: int
#     preview_url: str
#     track_number: int
#     type: str
#     uri: str

class TrackItem(TypedDict):
    album: dict
    artists: list
    available_markets: list
    disc_number: int
    duration_ms: int
    explicit: bool
    external_ids: dict
    external_urls: dict
    href: str
    id: str
    is_local: bool
    is_playable: bool
    name: str
    popularity: int
    preview_url: str | None  # always null for apps created after Nov 2024
    track_number: int
    type: str
    uri: str
    # Only present in some responses (track relinking / market restrictions).
    # Last on purpose, so the columns before them keep their position.
    linked_from: NotRequired[dict]
    restrictions: NotRequired[dict]


class EpisodeItem(TypedDict):
    '''
    Podcast episode, as returned inside playlists next to normal tracks.
    Written to its own CSV, because the fields differ from a track.
    '''
    audio_preview_url: str | None
    description: str
    duration_ms: int
    explicit: bool
    external_urls: dict
    href: str
    id: str
    images: list
    is_externally_hosted: bool
    is_playable: bool
    language: str
    languages: list
    name: str
    release_date: str
    release_date_precision: str
    show: dict
    type: str
    uri: str
    restrictions: NotRequired[dict]


class Track(TypedDict):
    added_at: str
    track: TrackItem


# Spotify ids are 22 characters of base62 (letters and digits).
PLAYLIST_ID = r"[0-9A-Za-z]{22}"
PLAYLIST_PATTERNS = [
    # bare id
    re.compile(rf"({PLAYLIST_ID})"),
    # spotify:playlist:<id> (and the old spotify:user:<name>:playlist:<id>)
    re.compile(rf"spotify:(?:user:[^:]+:)?playlist:({PLAYLIST_ID})"),
    # https://open.spotify.com/[intl-xx/]playlist/<id>[?si=...]
    re.compile(r"https?://open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]+)?/)?"
               rf"playlist/({PLAYLIST_ID})(?:[/?#].*)?"),
]


def extract_playlist_id(value: str) -> str:
    '''
    Accepts a bare playlist id, a Spotify URI (spotify:playlist:<id>)
    or an open.spotify.com playlist link (with or without query params)
    and returns the bare playlist id.
    Raises ValueError for anything else (album/track links, typos, ...).
    '''
    # Old version (kept for reference): accepted anything, so an album link
    # or a typo went to the API as-is and ended in a confusing 404.
    # match = re.search(r"playlist[/:]([a-zA-Z0-9]+)", value)
    # if match:
    #     return match.group(1)
    # return value.strip()
    value = value.strip()
    for pattern in PLAYLIST_PATTERNS:
        match = pattern.fullmatch(value)
        if match:
            return match.group(1)
    raise ValueError(f"not a Spotify playlist id, URI or link: {value!r}")


def _paginate(user: spotipy.Spotify, first_page) -> list[Track]:
    '''
    Follows the "next" links of a paged Spotify response, starting from
    first_page, and returns the items of all pages in one list.
    Shared by get_all_tracks and get_playlist_tracks (same loop in both).
    '''
    tracks: list[Track] = []
    response = first_page
    while response:
        tracks.extend(response["items"])
        response = user.next(response) if response.get("next") else None
    return tracks


# Renamed from getAllTracks / getPlaylistTracks to snake_case (PEP 8).
def get_all_tracks(user: spotipy.Spotify, limit_step=50):
    '''
    Function to obtain all tracks saved in the current user's library
    ("Liked Songs").\n
    returns list of saved-track items: {"added_at": ..., "track": {...}}
    '''
    # Old version (kept for reference), now handled by _paginate():
    # tracks: list[Track] = []
    # response = user.current_user_saved_tracks(limit=limit_step)
    # while response:
    #     tracks.extend(response["items"])
    #     response = user.next(response) if response.get("next") else None
    # return tracks
    first_page = user.current_user_saved_tracks(limit=limit_step)
    return _paginate(user, first_page)


def get_playlist_tracks(user: spotipy.Spotify, playlist_id: str,
                        limit_step=100):
    '''
    Function to obtain all tracks of a given playlist (by id, URI or link).\n
    Works for public, private and collaborative playlists the authenticated
    user has access to.
    '''
    # Old version (kept for reference), now handled by _paginate():
    # tracks: list[Track] = []
    # response = user.playlist_items(playlist_id, limit=limit_step)
    # while response:
    #     tracks.extend(response["items"])
    #     response = user.next(response) if response.get("next") else None
    # return tracks
    first_page = user.playlist_items(playlist_id, limit=limit_step)
    return _paginate(user, first_page)


def to_cell(value: Any):
    '''
    Nested values (dicts / lists such as album, artists, external_urls) are
    written as compact JSON so they can be parsed back with any JSON parser.
    Scalars are left to the csv module as-is.
    '''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


# Debug helper, never called anywhere (was used to find out which Python
# types each API field has, which is how TrackItem above was written).
# def checks_attributes(tracks: list[Track]):
#     types: dict[str, set[str]] = {}
#     for track in tracks:
#         track_data: dict[str,Any] = track["track"];
#         for k, v in track_data.items():
#             if k not in types:
#                 types[k] = set()
#             types[k].add(type(v))
#     return types


def split_items(items: list[dict]):
    '''
    Splits playlist/library items into (tracks, episodes).
    Each result is a list of flat dicts: {"added_at": ..., **item_fields}.
    Items without data (local files, unavailable items) are dropped.
    '''
    tracks: list[dict] = []
    episodes: list[dict] = []
    for entry in items:
        # "track" is the documented key; "item" is tolerated in case the
        # API renames it (newer playlist responses may use it).
        data = entry.get("track") or entry.get("item")
        if not data:
            # local files / unavailable items can have no track data
            continue
        row = {"added_at": entry.get("added_at")} | data
        if data.get("type") == "episode":
            episodes.append(row)
        else:
            tracks.append(row)
    return tracks, episodes


def write_csv(stream, item_type: type, rows: list[dict]):
    '''Writes rows as ;-delimited CSV, columns in a fixed order.'''
    field_names = ["added_at", *item_type.__annotations__]
    writer = csv.DictWriter(stream, fieldnames=field_names, delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: to_cell(row.get(k)) for k in field_names})
    stream.flush()


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(
        description="Export Liked Songs or a playlist to CSV (stdout).")
    parser.add_argument(
        "playlist", nargs="?",
        help="playlist link, spotify:playlist:<id> URI or bare id "
             "(default: your Liked Songs)")
    parser.add_argument(
        "--episodes-out", metavar="FILE",
        help="write podcast episodes found in the playlist to this CSV "
             "file (otherwise they are skipped)")
    return parser.parse_args(argv)


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    # user-library-read is needed for "Liked Songs", the playlist-read-*
    # scopes are needed to read private/collaborative playlists by link.
    scope = ("user-library-read playlist-read-private "
             "playlist-read-collaborative")
    auth_manager = SpotifyOAuth(
        scope=scope,
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        cache_path=os.path.join(BASE_DIR, ".cache"),
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Optional playlist argument; if omitted, falls back to the user's saved
    # tracks ("Liked Songs").
    # Old version (kept for reference), before --episodes-out existed:
    # playlist_arg = sys.argv[1] if len(sys.argv) > 1 else None
    args = parse_args(sys.argv[1:])
    playlist_arg = args.playlist

    if playlist_arg:
        try:
            playlist_id = extract_playlist_id(playlist_arg)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            print("expected: a playlist link "
                  "(https://open.spotify.com/playlist/<id>), a "
                  "spotify:playlist:<id> URI or a 22-character id",
                  file=sys.stderr)
            sys.exit(2)
        items = get_playlist_tracks(sp, playlist_id)
    else:
        items = get_all_tracks(sp)

    # The csv module writes its own line endings and expects the stream to
    # not translate them. Without this, Windows turns "\r\n" into "\r\r\n"
    # (a blank line between rows).
    sys.stdout.reconfigure(newline="")

    # Old version (kept for reference): every item was written as a track
    # row, so podcast episodes ended up as rows with most columns empty.
    # field_names = ["added_at", *TrackItem.__annotations__]
    # writer = csv.DictWriter(sys.stdout, fieldnames=field_names,
    #                         delimiter=";")
    # writer.writeheader()
    # for track in tracks:
    #     track_data = track.get("track")
    #     if not track_data:
    #         continue
    #     data = {"added_at": track["added_at"]} | track_data
    #     writer.writerow({k: to_cell(data.get(k)) for k in field_names})
    songs, episodes = split_items(items)
    write_csv(sys.stdout, TrackItem, songs)

    if episodes and args.episodes_out:
        with open(args.episodes_out, "w", newline="",
                  encoding="utf-8") as episodes_file:
            write_csv(episodes_file, EpisodeItem, episodes)
        print(f"wrote {len(episodes)} episodes to {args.episodes_out}",
              file=sys.stderr)
    elif episodes:
        print(f"skipped {len(episodes)} episodes "
              "(use --episodes-out FILE to export them)", file=sys.stderr)


if __name__ == "__main__":
    main()
