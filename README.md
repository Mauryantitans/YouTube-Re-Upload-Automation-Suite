# YouTube Video Upload Automation

This project automates downloading videos from YouTube and reuploading them to your own YouTube channel with the same metadata.

---

## **📌 Features**
- Downloads a video from a given YouTube link
- Extracts metadata (title, description, tags, category)
- Uploads the video to your YouTube channel
- Uses the latest video first in case of multiple uploads

---

## **🔧 Setup & Installation**

### **1️⃣ Enable YouTube API**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **YouTube Data API v3**
4. Navigate to **Credentials** → "Create Credentials" → "OAuth Client ID"
5. Select **Application Type = "Desktop App"**
6. Click **Create**, then **Download JSON**
7. Rename and save it as **client_secrets.json** in your project directory

### **2️⃣ Install Dependencies**
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 googleapiclient yt-dlp
```

### **3️⃣ Authenticate & Run**
```bash
python youtube_auto_upload.py
```

### **4️⃣ First-Time Authentication**
1. The script will open a browser for Google sign-in
2. Click **Advanced** → **Go to Your App Name (Unsafe)**
3. Click **Allow** to grant YouTube upload permissions
4. The authentication will complete, and the script will run

---

## **📜 How It Works**
1. The script prompts for a **YouTube video URL**
2. It **downloads metadata** (title, description, tags, etc.)
3. It **downloads the actual video file**
4. It **uploads the video to your YouTube channel** with the same metadata

---

## **📂 Project Structure**
```
Youtube-Project/
│── client_secrets.json   # OAuth credentials (DO NOT SHARE!)
│── youtube_auto_upload.py  # Main script
│── test_upload/           # Folder for downloaded videos
│── README.md              # Project documentation
```

---

## **🛠 Troubleshooting**
### **Issue: "Access blocked: This app has not been verified"**
- Go to [Google Cloud OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
- Add your **Google account** under **Test Users**
- Save and try again

### **Issue: `redirect_uri_mismatch` or `access_denied`**
- Ensure the **client_secrets.json** path is correct
- Delete old credentials:
  ```bash
  rm -rf ~/.credentials/
  ```
- Restart the script

### **Issue: Quota Exceeded**
- Check [YouTube API Quotas](https://console.cloud.google.com/apis/dashboard)
- Reduce upload frequency

---

## **📢 Notes**
- This script is meant for **personal use** due to API limitations
- To make it **public**, you need to submit for **Google verification**

---

## **🚀 Future Improvements**
- Automate fetching videos from a full channel
- Schedule uploads with a time delay
- Add a simple web dashboard

---

## **📝 Author**
Created by [Your Name] 🚀