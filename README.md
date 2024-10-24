# Spotify Obtainer
This repo will:
- create simple venv environment inside script dir
- retrieve list of user spotify songs
- output songs in `csv` form to stdout
    - begins with **$BEGIN**, ends with **$END**

## Installation:
Create ./.env file with variables like this:
```sh
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=your_redirect_uri_here
```