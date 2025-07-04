import os
import json
import subprocess
import re
import glob
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# Set up API credentials (Download from Google Cloud Console)
CLIENT_SECRET_FILE = r"C:\Users\moury\OneDrive\Desktop\Youtube Project\Upload-Test\client_secrets.json"
TOKEN_FILE = "token.pickle"  # To store authentication token
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DOWNLOAD_FOLDER = "test_upload"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def authenticate_youtube():
    """Authenticate with YouTube API and return the service object."""
    credentials = None

    # Load saved credentials if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            credentials = pickle.load(token)

    # If credentials are not available or invalid, authenticate
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        credentials = flow.run_local_server(port=8080)

        # Save credentials for future use
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(credentials, token)
        print("✅ Credentials saved for future use.")

    return build("youtube", "v3", credentials=credentials)

def download_video(youtube_url):
    """Download video, metadata, and thumbnail using yt-dlp."""
    video_id = youtube_url.split("v=")[-1]

    command = [
        "yt-dlp",
        "--write-info-json",
        "--write-thumbnail",
        "--merge-output-format", "mp4",
        "-o", os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s"),
        youtube_url
    ]

    try:
        subprocess.run(command, check=True)
        print("✅ Metadata & thumbnail downloaded successfully.")
    except subprocess.CalledProcessError:
        print("❌ Failed to download metadata.")
        return None, None, None

    # Find metadata file
    metadata_file = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.info.json")
    if not os.path.exists(metadata_file):
        print("❌ Metadata file not found.")
        return None, None, None

    # Load metadata
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Find the actual video file
    video_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, f"{video_id}.*"))
    video_file = next((f for f in video_files if f.endswith(('.mp4', '.mkv', '.webm'))), None)
    
    if not video_file:
        print(f"❌ Error: No video file found for {video_id}")
        return None, None, None

    print(f"✅ Found correct video file: {video_file}")

    # Find the thumbnail file
    thumbnail_file = next((f for f in video_files if f.endswith(('.jpg', '.png', '.webp'))), None)

    return video_file, metadata, thumbnail_file

def upload_video(youtube, video_file, metadata, thumbnail_file):
    """Upload a video to YouTube with metadata and thumbnail."""
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata.get("title", "Untitled Video"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": str(metadata.get("category", 22)),  # Default to Entertainment
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    response = request.execute()
    video_id = response["id"]
    print(f"✅ Video uploaded successfully: https://www.youtube.com/watch?v={video_id}")

    # Upload thumbnail if available
    if thumbnail_file:
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print(f"✅ Thumbnail uploaded successfully: {thumbnail_file}")
        except Exception as e:
            print(f"⚠ Error uploading thumbnail: {e}")
    else:
        print("⚠ No thumbnail found, skipping thumbnail upload.")

if __name__ == "__main__":
    youtube_url = input("Enter YouTube video URL: ")

    youtube = authenticate_youtube()
    video_file, metadata, thumbnail_file = download_video(youtube_url)

    if video_file and metadata:
        upload_video(youtube, video_file, metadata, thumbnail_file)
