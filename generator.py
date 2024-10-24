import os, sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import NotRequired, TypedDict, Any
import csv
from dotenv import load_dotenv


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
    

def getAllTracks(user: spotipy.Spotify, limit_step=50):
    '''
    Function to obtain all user tracks.\n
    returns list['href', 'items', 'limit', 'next', 'offset', 'previous', 'total']
    '''
    tracks: list[Track] = []
    for off in range(0, 1000, limit_step):
        response = user.current_user_saved_tracks(
            limit=limit_step, offset=off
        )
        # print(type(response))
        # print
        # print(response)
        if len(response) == 0:
            break
        tracks.extend(response["items"])
    return tracks


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
    load_dotenv()
    scope = "user-library-read"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, client_id=os.getenv('SPOTIPY_CLIENT_ID'),client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI')))

    tracks =  getAllTracks(sp)
    # a = TrackItem.__annotations__
    # a = TrackItem.__required_keys__
    # print(a)
    # print(type(a))
    # types = checks_attributes(trakcs)

    field_names = {"added_at"}.union(TrackItem.__required_keys__)
    # with open(sys.stdout, "w") as csvfile:
    with sys.stdout as csvfile:
        # writer = csv.writer(csvfile, delimiter=';',quotechar="|",quoting=csv.QUOTE_MINIMAL)
        writer = csv.DictWriter(csvfile, fieldnames=field_names,
                    delimiter=";")
        writer.writeheader()
        for track in tracks:
            data = {"added_at": track["added_at"]} | (track["track"])
            writer.writerow(data)
            # print(data)

    # results = sp.current_user_saved_tracks(limit=50)
    # for idx, item in enumerate(results['items']):
    #     track = item['track']
    #     print(idx, track['artists'][0]['name'], " – ", track['name'])

if __name__ == "__main__": 
    main()
