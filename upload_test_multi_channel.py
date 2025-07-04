import os
import json
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from yt_dlp import YoutubeDL

# Project folder setup
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(PROJECT_FOLDER, "client_secrets.json")
TOKENS_DIR = os.path.join(PROJECT_FOLDER, "tokens")  # Store multiple tokens

# Ensure tokens directory exists
os.makedirs(TOKENS_DIR, exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Function to authenticate YouTube API
def authenticate_youtube(channel_name):
    token_path = os.path.join(TOKENS_DIR, f"{channel_name}.pickle")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token_file:
            credentials = pickle.load(token_file)
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        credentials = flow.run_local_server(port=8080)

        # Save the token
        with open(token_path, "wb") as token_file:
            pickle.dump(credentials, token_file)
        print(f"✅ Credentials saved for {channel_name}")

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

# Function to list available channels
def list_channels():
    return [f.split(".pickle")[0] for f in os.listdir(TOKENS_DIR) if f.endswith(".pickle")]

# Function to select or create a channel (follows the requested flow)
def select_channel():
    channels = list_channels()

    if not channels:
        print("\nNo saved channels found. Creating a new one.")
        return add_new_channel()
    
    if len(channels) == 1:
        print(f"\nOnly one saved channel found: {channels[0]}")
        use_existing = input(f"Do you want to upload to '{channels[0]}'? (y/n): ").strip().lower()
        if use_existing == "y":
            return channels[0]
        else:
            return add_new_channel()

    print("\nAvailable Channels:")
    for idx, channel in enumerate(channels, start=1):
        print(f"{idx}. {channel}")
    print(f"{len(channels) + 1}. Add a new channel")

    while True:
        try:
            choice = int(input("Select a channel (enter number): ")) - 1
            if 0 <= choice < len(channels):
                return channels[choice]
            elif choice == len(channels):
                return add_new_channel()
            else:
                print("❌ Invalid choice. Try again.")
        except ValueError:
            print("❌ Enter a valid number.")

# Function to add a new channel
def add_new_channel():
    channel_name = input("Enter a name for the new channel: ").strip()
    authenticate_youtube(channel_name)
    return channel_name

# Function to download a video and metadata
def download_video(video_url, download_path="test_upload"):
    os.makedirs(download_path, exist_ok=True)
    ydl_opts = {
        "outtmpl": os.path.join(download_path, "%(id)s.%(ext)s"),
        "writethumbnail": True,
        "writeinfojson": True,
        "merge_output_format": "mp4",
        "format": "bestvideo+bestaudio/best"
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

    video_file = os.path.join(download_path, f"{info['id']}.mp4")
    thumbnail_file = os.path.join(download_path, f"{info['id']}.webp")
    metadata_file = os.path.join(download_path, f"{info['id']}.info.json")

    return video_file, thumbnail_file, metadata_file, info

# Function to upload video
def upload_video(youtube, video_file, metadata_file, thumbnail_file):
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata.get("title", "Untitled Video"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": metadata.get("category", "22"),
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=googleapiclient.http.MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    response = request.execute()
    video_id = response.get("id")
    print(f"✅ Video uploaded successfully: https://www.youtube.com/watch?v={video_id}")

    # Upload thumbnail
    if os.path.exists(thumbnail_file):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=googleapiclient.http.MediaFileUpload(thumbnail_file)
            ).execute()
            print(f"✅ Thumbnail uploaded successfully: {thumbnail_file}")
        except googleapiclient.errors.HttpError as e:
            print(f"⚠ Error uploading thumbnail: {e}")

# Main script
if __name__ == "__main__":
    selected_channel = select_channel()
    youtube = authenticate_youtube(selected_channel)

    video_url = input("Enter YouTube video URL: ").strip()
    video_file, thumbnail_file, metadata_file, info = download_video(video_url)

    upload_video(youtube, video_file, metadata_file, thumbnail_file)
