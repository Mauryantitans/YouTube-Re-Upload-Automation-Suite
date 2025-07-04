import os
import json
import pickle
import subprocess
import re
import glob
import pytz
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from openai import OpenAI

# Load configuration
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from file."""
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()

CLIENT_SECRET_FILE = config["CLIENT_SECRET_FILE"]
TOKENS_DIR = config["TOKENS_DIR"]
DOWNLOAD_FOLDER = config["DOWNLOAD_FOLDER"]
API_KEY = config["OPENAI_API_KEY"]
USER_TIMEZONE = config.get("TIMEZONE", "UTC")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Ensure tokens directory exists
os.makedirs(TOKENS_DIR, exist_ok=True)

def authenticate_youtube(channel_name):
    """Authenticate with YouTube API and return the service object."""
    token_path = os.path.join(TOKENS_DIR, f"{channel_name}.pickle")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token_file:
            credentials = pickle.load(token_file)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        credentials = flow.run_local_server(port=8080)

        with open(token_path, "wb") as token_file:
            pickle.dump(credentials, token_file)
        print(f"✅ Credentials saved for {channel_name}")

    return build("youtube", "v3", credentials=credentials)

def list_channels():
    """List available YouTube channel tokens."""
    return [f.split(".pickle")[0] for f in os.listdir(TOKENS_DIR) if f.endswith(".pickle")]

def select_channel():
    """Select an existing channel or add a new one."""
    channels = list_channels()
    
    if not channels:
        return add_new_channel()
    
    print("\nAvailable Channels:")
    for idx, channel in enumerate(channels, start=1):
        print(f"{idx}. {channel}")
    print(f"{len(channels) + 1}. Add a new channel")

    while True:
        try:
            choice = int(input("Select a channel: ")) - 1
            if 0 <= choice < len(channels):
                return channels[choice]
            elif choice == len(channels):
                return add_new_channel()
            else:
                print("❌ Invalid choice. Try again.")
        except ValueError:
            print("❌ Enter a valid number.")

def add_new_channel():
    """Add a new channel and authenticate."""
    channel_name = input("Enter a name for the new channel: ").strip()
    authenticate_youtube(channel_name)
    return channel_name

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
    except subprocess.CalledProcessError:
        print("❌ Failed to download video.")
        return None, None, None

    metadata_file = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.info.json")
    if not os.path.exists(metadata_file):
        print("❌ Metadata file not found.")
        return None, None, None

    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    video_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, f"{video_id}.*"))
    video_file = next((f for f in video_files if f.endswith(('.mp4', '.mkv', '.webm'))), None)
    thumbnail_file = next((f for f in video_files if f.endswith(('.jpg', '.png', '.webp'))), None)

    return video_file, metadata, thumbnail_file

def filter_description(original_description):
    """Use ChatGPT to filter the video description."""
    client = OpenAI(api_key=API_KEY)
    system_prompt = "Remove all information related to the original channel, including links, calls to subscribe, and mentions, while keeping the rest of the description intact."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_description}
            ]
        )
        filtered_description = response.choices[0].message.content
    except Exception as e:
        print(f"⚠ ChatGPT API error: {e}")
        filtered_description = original_description

    return filtered_description

def convert_to_utc(local_time_str):
    """Convert local scheduled time to UTC."""
    local_tz = pytz.timezone(USER_TIMEZONE)
    local_time = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M")
    local_time = local_tz.localize(local_time)
    return local_time.astimezone(pytz.utc)

def upload_video(youtube, video_file, metadata, thumbnail_file, schedule_time=None):
    """Upload a video to YouTube with metadata and thumbnail."""
    filtered_description = filter_description(metadata.get("description", ""))

    copyright_notice = "\n\n⚠ This video is reuploaded for educational or informational purposes under fair use."
    final_description = filtered_description + copyright_notice

    body = {
        "snippet": {
            "title": metadata.get("title", "Untitled Video"),
            "description": final_description,
            "tags": metadata.get("tags", []),
            "categoryId": str(metadata.get("category", 22)),
        },
        "status": {
            "privacyStatus": "private" if schedule_time else "public"
        }
    }

    if schedule_time:
        body["status"]["publishAt"] = schedule_time.isoformat()

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    response = request.execute()
    video_id = response["id"]
    print(f"✅ Video uploaded successfully: https://www.youtube.com/watch?v={video_id}")

    if thumbnail_file:
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print(f"✅ Thumbnail uploaded successfully: {thumbnail_file}")
        except Exception as e:
            print(f"⚠ Error uploading thumbnail: {e}")

def get_scheduled_time():
    """Ask user for a scheduled upload time."""
    choice = input("Do you want to schedule this video? (yes/no): ").strip().lower()
    if choice != "yes":
        return None

    while True:
        try:
            date_str = input("Enter scheduled time (YYYY-MM-DD HH:MM): ").strip()
            schedule_time = convert_to_utc(date_str)
            print(f"📅 Video will be scheduled for {schedule_time} UTC.")
            return schedule_time
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD HH:MM.")

if __name__ == "__main__":
    selected_channel = select_channel()
    youtube = authenticate_youtube(selected_channel)

    youtube_url = input("Enter YouTube video URL: ").strip()
    video_file, metadata, thumbnail_file = download_video(youtube_url)

    if video_file and metadata:
        schedule_time = get_scheduled_time()
        upload_video(youtube, video_file, metadata, thumbnail_file, schedule_time)
