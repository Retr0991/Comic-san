import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Get latest chapter
def get_latest_chapter(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Find the specific div with the given class
    find_spans = soup.find_all('span', class_="pl-[1px]")

    if not find_spans:
        print("Chapter not found")
        return
    chapter = find_spans[1].text

    return chapter


# Download image
def download_image(img_url, folder, counter):
    try:
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            print(os.path.basename(img_url), end=' ')
            if os.path.basename(img_url) == 'logo.webp':
                return
            # Define the file name using the counter
            # and use the alraedy existing extension
            img_name = f"{counter:03d}.{os.path.basename(img_url).split('.')[-1]}"
            # Define the file path
            img_path = os.path.join(folder, img_name)
            # Save the image content
            with open(img_path, 'wb') as f:
                f.write(img_response.content)
            print(f"Downloaded {img_name}")
        else:
            print(f"Failed to retrieve {img_url}")
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")

# Scrape all images from a specific div
def scrape_webp_images(url: str, folder: str):
    # Send GET
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the specific div with the given class
    div = soup.find('div', class_="py-8 -mx-5 md:mx-0 flex flex-col items-center justify-center")

    if not div:
        print("Div not found")
        return

    img_tags = div.find_all('img')

    if not os.path.exists(folder):
        os.makedirs(folder)

    # Initialize counter 
    counter = 1

    for img in img_tags:
        img_url = img.get('src')
        # Take in all image formats
        if img_url and (img_url.lower().endswith('.webp') or img_url.lower().endswith('.jpg')
                        or img_url.lower().endswith('.jpeg') or img_url.lower().endswith('.png')):
            
            img_url = urljoin(url, img_url) # Create the full URL for the image
            download_image(img_url, folder, counter)
            counter += 1


# Example usage
if __name__ == '__main__':
    website_url = "https://asuracomic.net/series/childhood-friend-of-the-zenith-ab07d211"
    # save_folder = "images"
    # scrape_webp_images(website_url, save_folder)
    get_latest_chapter(website_url)
