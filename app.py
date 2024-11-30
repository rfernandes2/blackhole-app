from settings import CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD, URL, PHOTO_DIR, URL_POST
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import requests
import os
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
import html
import shutil
from io import BytesIO
from zipfile import ZipFile
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Create Flask app instance
app = Flask(__name__)

# Ensure image directory exists, if not create it
os.makedirs(PHOTO_DIR, exist_ok=True)

# Route to render the homepage
@app.route("/")
def index():
    return render_template("index.html")

# Route to handle authentication with Reddit and retrieve the access token
@app.route("/auth", methods=["POST"])
def authenticate():
    # Reddit authentication request data
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    # Basic Authentication with client credentials
    auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    # Headers for the request
    headers = {"User-Agent": "YourApp/0.1"}

    try:
        # Send POST request to Reddit API to get the access token
        response = requests.post(f'{URL}/api/v1/access_token', data=data, auth=auth, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        # Extract the token from the response
        token = response.json().get("access_token")
        return jsonify({"token": token})  # Return the token as JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if the request fails

# Route to fetch images from a Reddit post based on the post URL and access token
@app.route("/fetch-images", methods=["POST"])
def fetch_images():
    data = request.json  # Get the JSON data from the request
    token = data.get("token")  # Access token to authenticate with Reddit
    post_url = data.get("url")  # Reddit post URL

    # Extract the post ID from the Reddit URL
    parsed_url = urlparse(post_url)
    path_parts = parsed_url.path.strip("/").split("/")
    if "comments" not in path_parts:
        return jsonify({"error": "Invalid Reddit URL"}), 400  # Return error if the URL is invalid

    post_id = path_parts[path_parts.index("comments") + 1]  # Get the post ID from the URL
    api_url = f"{URL_POST}/comments/{post_id}"  # URL for fetching post comments via Reddit API

    # Set headers including the Bearer token for authorization
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "YourApp/0.1"}

    try:
        # Fetch the post data from Reddit API
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        post_data = response.json()  # Parse the JSON response
        images = []  # List to store the image URLs

        # Check if the post contains media (gallery posts)
        post = post_data[0]["data"]["children"][0]["data"]
        if "media_metadata" in post:  # For gallery posts
            for _, item in post["media_metadata"].items():
                url = html.unescape(item["p"][-1]["u"])  # Extract image URL
                images.append(url)
        elif post.get("url", "").endswith(("jpg", "png", "jpeg")):  # For single image posts
            images.append(post["url"])

        # Download images and save them to the local folder
        downloaded = []  # List to store paths of downloaded images
        for url in images:
            file_name = os.path.basename(urlparse(url).path)  # Get the image file name
            file_path = os.path.join(PHOTO_DIR, file_name)  # Full path to save the image
            with requests.get(url, stream=True) as r:
                r.raise_for_status()  # Raise an error if the request fails
                with open(file_path, "wb") as f:  # Save the image file
                    f.write(r.content)
            downloaded.append(f"/images/{file_name}")  # Append the image path to the list

        return jsonify({"images": downloaded})  # Return the list of downloaded image paths as JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if fetching images fails

# Route to serve images to the client when requested by filename
@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(PHOTO_DIR, filename)  # Serve image from PHOTO_DIR

# Route to download all images in the folder as a ZIP file
@app.route("/download-images", methods=["POST"])
def download_images():
    """
    Create a ZIP of all the images in the PHOTO_DIR and send it to the client.
    After downloading, clean up the PHOTO_DIR.
    """
    try:
        # Create a BytesIO object to hold the ZIP file in memory
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            # Add all images in PHOTO_DIR to the ZIP
            for filename in os.listdir(PHOTO_DIR):
                file_path = os.path.join(PHOTO_DIR, filename)
                if os.path.isfile(file_path):  # Check if it's a file (not a directory)
                    zip_file.write(file_path, filename)  # Write the file to the ZIP archive

        zip_buffer.seek(0)  # Rewind the buffer to the beginning
        # Send the ZIP file as a response for downloading
        response = send_file(zip_buffer, as_attachment=True, download_name="reddit_images.zip", mimetype="application/zip")

        # Clean up the PHOTO_DIR by removing all files after zipping
        shutil.rmtree(PHOTO_DIR)  # Delete all files in PHOTO_DIR
        os.makedirs(PHOTO_DIR)  # Recreate the directory

        return response  # Return the ZIP file as an attachment for download
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if ZIP creation fails

# Run the Flask app in debug mode
if __name__ == "__main__":
    app.run(debug=True)
