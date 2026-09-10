import requests
import zipfile
import os

API_URL = "http://localhost:8000/export_record_data"
with open("password/token_for_ai_dev.txt", "r") as f:
    AI_TOKEN = f.read().strip()

print("Downloading dataset from server. Please wait...")
response = requests.get(
    API_URL, 
    headers={"ai-token": AI_TOKEN}, 
    stream=True
)

if response.status_code == 200:
    downloads_dir = os.path.expanduser("~/Downloads")
    
    zip_file_path = os.path.join(downloads_dir, "water_record_dataset.zip")
    extract_dir = os.path.join(downloads_dir, "Water_record_dataset")

    with open(zip_file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    with zipfile.ZipFile(zip_file_path, 'r') as z:
        z.extractall(extract_dir)
        
    print("Downloaded successfully!")
    print(f" - Zip file saved at: {zip_file_path}")
    print(f" - Extracted data at: {extract_dir}")
else:
    print(f"Error: {response.json()}")