import json
import os
from wcmatch import pathlib
import yt_dlp
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors
import requests

os.chdir(pathlib.Path(__file__).parent.resolve())

with open("yt-dlp-playlist-config.json", "r") as tmp:
    config = json.load(tmp)

archiveAllUserPlaylists = config["archiveAllUserPlaylists"]
archiveLikedVideos = config["archiveLikedVideos"]
archiveWatchLater = config["archiveWatchLater"]
downloadBaseDirectory = config["downloadBaseDirectory"]
ffmpegLocation = config["ffmpegLocation"]
outputFileFormat = config["outputFileFormat"]
playlists = config["playlists"]
oauthClientSecretsFile = config["oauthClientSecretsFile"]

ydl_opts = {
  'cookiesfrombrowser': ('firefox', ),
  'ffmpeg_location': ffmpegLocation,
  'merge_output_format': outputFileFormat,
  'ignoreerrors': True,
  'windowsfilenames': True,
  'subtitleslangs': 'all,-live_chat',
  'postprocessors': [
      {
          'key': 'FFmpegEmbedSubtitle',
      },
      {
          'key': 'FFmpegThumbnailsConvertor',
          'format': 'png',
      },
      {
          'key': 'FFmpegSubtitlesConvertor',
          'format': 'ass',
      },
      {
          'key': 'FFmpegMetadata',
          'add_metadata': True,
          'add_chapters': True,
      },
      {
          'key': 'EmbedThumbnail',
      },
  ],
}

def getUserPlaylists():
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
        maxResults=50,
        mine=True
    )
    response = request.execute()

    playlists_response = {}
    for item in response['items']:
        name = item['snippet']['title']
        url = "https://www.youtube.com/playlist?list=" + item['id']
        playlists_response[name] = url

    return playlists_response

def cleanDirectory():
    files_to_remove = list(pathlib.Path(downloadBaseDirectory).rglob(['*.webm', '*.temp.*']))
    for file in files_to_remove:
        pathlib.Path(file).unlink(missing_ok=True)

def createDirectory(directoryName):
    pathlib.Path(directoryName).mkdir(parents=False, exist_ok=True)

def downloadPlaylists(playlists):
    for name, value in playlists.items():
        playlistDirectory = name.strip()
        createDirectory(playlistDirectory)
        ydl_opts['outtmpl'] = downloadBaseDirectory + playlistDirectory + '/%(title)s - %(channel)s - %(upload_date)s'
        ydl_opts['download_archive'] = playlistDirectory + "/" + playlistDirectory.lower() + '.txt'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(value)

if __name__ == "__main__":
    if archiveAllUserPlaylists:
        userPlaylists = getUserPlaylists()
        playlists.update(userPlaylists)
    if archiveLikedVideos:
        playlists['Liked Videos'] = "https://www.youtube.com/playlist?list=LL"
    if archiveWatchLater:
        playlists['Watch Later'] = "https://www.youtube.com/playlist?list=WL"

    os.chdir(downloadBaseDirectory)
    downloadPlaylists(playlists)
    cleanDirectory()
