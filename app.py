from flask import Flask, render_template, request, jsonify
import json
import os
import time
import threading
import yt_dlp
from datetime import datetime
from googleapiclient.discovery import build

app = Flask(__name__)

DATA_FILE = "channel_data.json"

# Load channel data
def load_channel_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}

# Save channel data
def save_channel_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Extract uploaded videos from a channel
def get_uploaded_videos(channel_url, start_date):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "force_generic_extractor": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        if "entries" in info:
            videos = [
                vid["url"] for vid in info["entries"]
                if "url" in vid and "upload_date" in vid and vid["upload_date"] >= start_date.replace("-", "")
            ]
            return videos
    return []

# Upload video function (Replace this with your existing upload logic)
def upload_video(video_url):
    print(f"Uploading: {video_url}")
    time.sleep(5)  # Simulating upload delay
    return True  # Return success

# Background thread for continuous checking
def video_checker():
    while True:
        channel_data = load_channel_data()
        if not channel_data.get("input_channel") or not channel_data.get("start_date"):
            time.sleep(60)
            continue

        input_channel = channel_data["input_channel"]
        start_date = channel_data["start_date"]
        uploaded_videos = set(channel_data.get("uploaded_videos", []))

        new_videos = set(get_uploaded_videos(input_channel, start_date))
        missing_videos = new_videos - uploaded_videos

        if missing_videos:
            print(f"Found {len(missing_videos)} new videos!")
            for video in missing_videos:
                if upload_video(video):
                    uploaded_videos.add(video)

        channel_data["uploaded_videos"] = list(uploaded_videos)
        channel_data["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_channel_data(channel_data)

        time.sleep(300)  # Check every 5 minutes

# Start background thread
threading.Thread(target=video_checker, daemon=True).start()

@app.route("/")
def index():
    channel_data = load_channel_data()
    return render_template("index.html", channels=["My Channel 1", "My Channel 2"], channel_data=channel_data)

@app.route("/set_channel", methods=["POST"])
def set_channel():
    data = request.json
    channel_data = {
        "input_channel": data.get("input_channel", "Not set"),
        "upload_channel": data.get("upload_channel", "Not set"),
        "start_date": data.get("start_date", "Not set"),
        "last_checked": "Not checked yet",
        "uploaded_videos": []
    }
    save_channel_data(channel_data)
    return jsonify({"message": "Settings saved!"})

@app.route("/get_uploaded_videos")
def get_uploaded_videos_route():
    channel_data = load_channel_data()
    return jsonify({"videos": channel_data.get("uploaded_videos", [])})

if __name__ == "__main__":
    app.run(debug=True)
