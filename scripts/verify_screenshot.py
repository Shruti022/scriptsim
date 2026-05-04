from google.cloud import storage
import os
from dotenv import load_dotenv

load_dotenv()

client = storage.Client()
bucket_name = "scriptsim-screenshots"
file_name = "homepage-missing-help-contact_1777771238.png"

print(f"Attempting to download gs://{bucket_name}/{file_name}")

try:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    if blob.exists():
        print("Blob exists!")
        print(f"Content-Type: {blob.content_type}")
        content = blob.download_as_bytes()
        print(f"Downloaded {len(content)} bytes.")
    else:
        print("Blob does NOT exist.")
except Exception as e:
    print(f"Error: {e}")
