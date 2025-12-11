import requests
from PIL import Image, ImageEnhance
from io import BytesIO
import os
import random

# Directory to save images
output_dir = "background_images"
os.makedirs(output_dir, exist_ok=True)

# URLs for royalty-free images (replace with actual URLs or API calls)
image_urls = [
    "https://loremflickr.com/800/600/nature",
    "https://loremflickr.com/800/600/forest",
    "https://loremflickr.com/800/600/mountain",
    "https://loremflickr.com/800/600/sky",
    "https://loremflickr.com/800/600/sea",
    "https://loremflickr.com/800/600/flowers",
    "https://loremflickr.com/800/600/sunset",
    "https://loremflickr.com/800/600/landscape",
    "https://loremflickr.com/800/600/trees",
    "https://loremflickr.com/800/600/clouds"
]

def download_and_process_images():
    for idx, url in enumerate(image_urls):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Open image
                img = Image.open(BytesIO(response.content))

                # Convert to RGBA (if not already)
                img = img.convert("RGBA")

                # Make the image pale by reducing opacity
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(0.3)  # Adjust brightness (0.3 = very pale)

                # Save the processed image
                output_path = os.path.join(output_dir, f"background_{idx + 1}.png")
                img.save(output_path, "PNG")
                print(f"Saved: {output_path}")
            else:
                print(f"Failed to download image {idx + 1}: {response.status_code}")
        except Exception as e:
            print(f"Error processing image {idx + 1}: {e}")

if __name__ == "__main__":
    download_and_process_images()