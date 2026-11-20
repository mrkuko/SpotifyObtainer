import json, os, re, sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import NotRequired, TypedDict, Any
import csv
from dotenv import load_dotenv


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


def getAllTracks(user: spotipy.Spotify, limit_step=50):
    '''
    Function to obtain all tracks saved in the current user's library ("Liked Songs").\n
    returns list['href', 'items', 'limit', 'next', 'offset', 'previous', 'total']
    '''
    tracks: list[Track] = []
    response = user.current_user_saved_tracks(limit=limit_step)
    while response:
        tracks.extend(response["items"])
        response = user.next(response) if response.get("next") else None
    return tracks


def getPlaylistTracks(user: spotipy.Spotify, playlist_id: str, limit_step=100):
    '''
    Function to obtain all tracks of a given playlist (by id, URI or link).\n
    Works for public, private and collaborative playlists the authenticated
    user has access to.
    '''
    tracks: list[Track] = []
    response = user.playlist_items(playlist_id, limit=limit_step)
    while response:
        tracks.extend(response["items"])
        response = user.next(response) if response.get("next") else None
    return tracks


def to_cell(value: Any):
    '''
    Nested values (dicts / lists such as album, artists, external_urls) are
    written as compact JSON so they can be parsed back with any JSON parser.
    Scalars are left to the csv module as-is.
    '''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def checks_attributes(tracks: list[Track]):
    types: dict[str, set[str]] = {}
    for track in tracks:
        track_data: dict[str,Any] = track["track"];
        for k, v in track_data.items():
            if k not in types:
                types[k] = set()
            types[k].add(type(v))
    return types


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    # user-library-read is needed for "Liked Songs", the playlist-read-*
    # scopes are needed to read private/collaborative playlists by link.
    scope = "user-library-read playlist-read-private playlist-read-collaborative"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=os.getenv('SPOTIPY_CLIENT_ID'),client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),cache_path=os.path.join(BASE_DIR, ".cache")))

    # Optional first CLI argument: playlist link, spotify:playlist:<id> URI or bare id.
    # If omitted, falls back to the user's saved tracks ("Liked Songs").
    playlist_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if playlist_arg:
        tracks = getPlaylistTracks(sp, extract_playlist_id(playlist_arg))
    else:
        tracks = getAllTracks(sp)

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
