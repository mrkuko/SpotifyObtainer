import csv
import json
import os
import re
import sys
from typing import Any, TypedDict

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


# .env and the spotipy token cache live next to this file, not in the cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
    preview_url: str
    track_number: int
    type: str
    uri: str


class Track(TypedDict):
    added_at: str
    track: TrackItem


def extract_playlist_id(value: str) -> str:
    '''
    Accepts a bare playlist id, a Spotify URI (spotify:playlist:<id>)
    or an open.spotify.com playlist link (with or without query params)
    and returns the bare playlist id.
    '''
    match = re.search(r"playlist[/:]([a-zA-Z0-9]+)", value)
    if match:
        return match.group(1)
    return value.strip()


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

    # Optional first CLI argument: playlist link, spotify:playlist:<id> URI
    # or bare id.
    # If omitted, falls back to the user's saved tracks ("Liked Songs").
    playlist_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if playlist_arg:
        tracks = get_playlist_tracks(sp, extract_playlist_id(playlist_arg))
    else:
        tracks = get_all_tracks(sp)

    field_names = ["added_at", *TrackItem.__annotations__]
    with sys.stdout as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names,
                                delimiter=";")
        writer.writeheader()
        for track in tracks:
            track_data = track.get("track")
            if not track_data:
                # local files / unavailable items can have no track data
                continue
            data = {"added_at": track["added_at"]} | track_data
            writer.writerow({k: to_cell(data.get(k)) for k in field_names})


if __name__ == "__main__":
    main()
