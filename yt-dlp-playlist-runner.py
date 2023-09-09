import json
import os
from wcmatch import pathlib
import yt_dlp
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors
import requests

with open("yt-dlp-playlist-config.json", "r") as tmp:
    config = json.load(tmp)

archiveAllPlaylists = config["archiveAllPlaylists"]
downloadBaseDirectory = config["downloadBaseDirectory"]
ffmpegLocation = config["ffmpegLocation"]
fileFormat = config["fileFormat"]
playlists = config["playlists"]
oauthClientSecretsFile = config["oauthClientSecretsFile"]
ydl_opts = config["ydl_opts"]

def getPlaylists():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = oauthClientSecretsFile

    credentials = None
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', scopes)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, scopes)
            credentials = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    request = youtube.playlists().list(
        part="snippet",
        mine=True
    )
    response = request.execute()

    # parse playlists here
    playlists_response = {}
    for item in response['items']:
        name = item['snippet']['title']
        url = "https://www.youtube.com/playlist?list=" + item['id']
        playlists_response[name] = url
    print(playlists_response)

def cleanDirectory():
    files_to_remove = list(pathlib.Path(downloadBaseDirectory).rglob(['*.webm', '*.temp.*']))
    for file in files_to_remove:
        pathlib.Path(file).unlink(missing_ok=True)

def createDirectory(directoryName):
    pathlib.Path(directoryName).mkdir(parents=False, exist_ok=True)

if __name__ == "__main__":
    if archiveAllPlaylists:
        getPlaylists()
    os.chdir(downloadBaseDirectory)
    for name, value in playlists.items():
        playlistDirectory = name.strip()
        createDirectory(playlistDirectory)
        ydl_opts['outtmpl'] = downloadBaseDirectory + playlistDirectory + '/%(title)s - %(channel)s - %(upload_date)s'
        ydl_opts['download_archive'] = playlistDirectory + "/" + playlistDirectory.lower() + '.txt'
        print(ydl_opts)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(value["url"])
    cleanDirectory()
