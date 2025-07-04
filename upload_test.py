import os
import json
import subprocess
import re
import glob
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# Set up API credentials (Download from Google Cloud Console)
CLIENT_SECRET_FILE = r"C:\Users\moury\OneDrive\Desktop\Youtube Project\Upload-Test\client_secrets.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DOWNLOAD_FOLDER = "test_upload"

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def authenticate_youtube():
    """Authenticate with YouTube API and return the service object."""
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    credentials = flow.run_local_server(port=8080)
    return build("youtube", "v3", credentials=credentials)

def download_video(youtube_url):
    """Download video and metadata using yt-dlp."""
    command = [
        "yt-dlp",
        "--write-info-json",
        "--skip-download",
        "-o", os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        youtube_url
    ]

    try:
        subprocess.run(command, check=True)
        print("Metadata downloaded successfully.")
    except subprocess.CalledProcessError:
        print("Failed to download metadata.")
        return None, None

    # Find metadata file
    for file in os.listdir(DOWNLOAD_FOLDER):
        if file.endswith(".json"):
            with open(os.path.join(DOWNLOAD_FOLDER, file), "r", encoding="utf-8") as f:
                metadata = json.load(f)
            video_title = metadata["title"]
            return video_title, metadata

    print("Metadata file not found.")
    return None, None

def upload_video(youtube, video_path, metadata):
    """Upload a video to YouTube with metadata."""
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata.get("tags", []),
                "categoryId": str(metadata.get("category", 22)),  # Default to Entertainment category
            },
            "status": {
                "privacyStatus": "public"  # Change to "private" if needed
            }
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    response = request.execute()
    print(f"Uploaded successfully: https://www.youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    youtube_url = input("Enter YouTube video URL: ")
    
    youtube = authenticate_youtube()  # Authenticate with YouTube API
    title, metadata = download_video(youtube_url)

    if title and metadata:
        # video_file = os.path.join(DOWNLOAD_FOLDER, f"{title}.mp4")

        # Remove invalid characters from filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)  # Remove special characters
        # video_file = os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.mp4")

        # Get the actual file with any extension
        video_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.*"))

        if not video_files:
            print(f"❌ Error: No video file found for {safe_title}")
            exit(1)

        video_file = video_files[0]  # Use the first matching file
        print(f"✅ Found video file: {video_file}")


        
        # Download actual video
        download_command = [
            "yt-dlp",
            "-o", video_file,
            youtube_url
        ]
        subprocess.run(download_command, check=True)

        # Upload to YouTube
        upload_video(youtube, video_file, metadata)
