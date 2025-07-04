import sys
import os
import json
import pickle
import subprocess
import glob
import pytz
import pyperclip
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QCheckBox, QDateTimeEdit, QMessageBox
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# Load configuration
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()
CLIENT_SECRET_FILE = config["CLIENT_SECRET_FILE"]
TOKENS_DIR = config["TOKENS_DIR"]
DOWNLOAD_FOLDER = config["DOWNLOAD_FOLDER"]
USER_TIMEZONE = config.get("TIMEZONE", "UTC")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Ensure tokens directory exists
os.makedirs(TOKENS_DIR, exist_ok=True)

class YouTubeUploaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.channels = self.list_channels()
        self.channel_dropdown.addItems(self.channels)

    def initUI(self):
        self.setWindowTitle("YouTube Uploader")
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("background-color: #222; color: white;")

        layout = QVBoxLayout()

        self.channel_label = QLabel("Select YouTube Channel:")
        layout.addWidget(self.channel_label)

        self.channel_dropdown = QComboBox()
        layout.addWidget(self.channel_dropdown)

        self.url_label = QLabel("Enter YouTube Video URL:")
        layout.addWidget(self.url_label)

        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)

        self.paste_button = QPushButton("Paste")
        self.paste_button.clicked.connect(self.paste_link)
        layout.addWidget(self.paste_button)

        self.schedule_checkbox = QCheckBox("Schedule Upload")
        self.schedule_checkbox.stateChanged.connect(self.toggle_datetime)
        layout.addWidget(self.schedule_checkbox)

        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_picker.setEnabled(False)
        layout.addWidget(self.datetime_picker)

        self.start_button = QPushButton("Start Process")
        self.start_button.clicked.connect(self.start_process)
        layout.addWidget(self.start_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def list_channels(self):
        return [f.split(".pickle")[0] for f in os.listdir(TOKENS_DIR) if f.endswith(".pickle")]

    def authenticate_youtube(self, channel_name):
        token_path = os.path.join(TOKENS_DIR, f"{channel_name}.pickle")
        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                credentials = pickle.load(token_file)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=8080)
            with open(token_path, "wb") as token_file:
                pickle.dump(credentials, token_file)
            self.log_output.append(f"✅ Credentials saved for {channel_name}")
        return build("youtube", "v3", credentials=credentials)

    def paste_link(self):
        self.url_input.setText(pyperclip.paste())

    def toggle_datetime(self):
        self.datetime_picker.setEnabled(self.schedule_checkbox.isChecked())

    def convert_to_utc(self, local_time):
        local_tz = pytz.timezone(USER_TIMEZONE)
        local_time = local_tz.localize(local_time)
        return local_time.astimezone(pytz.utc)

    def start_process(self):
        selected_channel = self.channel_dropdown.currentText()
        youtube_url = self.url_input.text().strip()

        if not youtube_url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube video URL.")
            return

        self.log_output.append(f"📥 Downloading video: {youtube_url}")
        video_file, metadata, thumbnail_file = self.download_video(youtube_url)

        if not video_file or not metadata:
            self.log_output.append("❌ Failed to download video.")
            return

        schedule_time = None
        if self.schedule_checkbox.isChecked():
            local_time = self.datetime_picker.dateTime().toPyDateTime()
            schedule_time = self.convert_to_utc(local_time)

        self.log_output.append("📤 Uploading video...")
        self.upload_video(selected_channel, video_file, metadata, thumbnail_file, schedule_time)

    def download_video(self, youtube_url):
        video_id = youtube_url.split("v=")[-1]
        command = [
            "yt-dlp", "--write-info-json", "--write-thumbnail", "--merge-output-format", "mp4",
            "-o", os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s"), youtube_url
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            return None, None, None

        metadata_file = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.info.json")
        if not os.path.exists(metadata_file):
            return None, None, None

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        video_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, f"{video_id}.*"))
        video_file = next((f for f in video_files if f.endswith(('.mp4', '.mkv', '.webm'))), None)
        thumbnail_file = next((f for f in video_files if f.endswith(('.jpg', '.png', '.webp'))), None)

        return video_file, metadata, thumbnail_file

    def upload_video(self, channel_name, video_file, metadata, thumbnail_file, schedule_time):
        youtube = self.authenticate_youtube(channel_name)

        body = {
            "snippet": {
                "title": metadata.get("title", "Untitled Video"),
                "description": metadata.get("description", "") + "\n\n⚠ Fair use disclaimer.",
                "tags": metadata.get("tags", []),
                "categoryId": str(metadata.get("category", 22)),
            },
            "status": {"privacyStatus": "private" if schedule_time else "public"}
        }

        if schedule_time:
            body["status"]["publishAt"] = schedule_time.isoformat()

        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
            )

            response = request.execute()
            video_id = response["id"]
            self.log_output.append(f"✅ Video uploaded successfully: https://www.youtube.com/watch?v={video_id}")

            if thumbnail_file:
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
                self.log_output.append(f"✅ Thumbnail uploaded successfully.")
        except Exception as e:
            self.log_output.append(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeUploaderApp()
    window.show()
    sys.exit(app.exec())
