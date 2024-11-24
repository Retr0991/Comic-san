import os
import requests
import asyncio
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright

DEBUG = False

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

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
def download_image(img_url, folder, counter, results):
    try:
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            print(os.path.basename(img_url), end=' ')
            if os.path.basename(img_url) == 'logo.webp':
                return
            # Define the file name using the counter
            # and use the already existing extension
            img_name = f"{counter:03d}.{os.path.basename(img_url).split('.')[-1]}"
            # Define the file path
            img_path = os.path.join(folder, img_name)
            # Save the image content
            with open(img_path, 'wb') as f:
                f.write(img_response.content)
            if DEBUG:
                print(f"Downloaded {img_name}")
            results[counter - 1] = img_name  # Store the result in the correct order
        else:
            print(f"Failed to retrieve {img_url}")
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")

# Scrape all images from a specific div
async def scrape_webp_images(url: str, folder: str):

    # Use Playwright to scrape the page
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        
        # Disable images and CSS to speed up loading
        await context.route("**/*", lambda route, request: route.abort() if request.resource_type in ["image", "stylesheet"] else route.continue_())
        
        page = await context.new_page()
        await page.goto(url)

        # Wait for the specific selector
        await page.wait_for_selector('.object-cover.mx-auto', timeout=2000)

        # Get the HTML source
        html_source = await page.content()
        await browser.close()

    # Find the specific img with the given class
    soup = BeautifulSoup(html_source, 'html.parser')
    img_tags = soup.find_all('img', class_="object-cover mx-auto")
    if DEBUG:
        print(len(img_tags))

    if not os.path.exists(folder):
        os.makedirs(folder)

    img_urls = []
    for img in img_tags:
        img_url = img.get('src')
        # Take in all image formats
        if img_url and (img_url.lower().endswith('.webp') or img_url.lower().endswith('.jpg')
                        or img_url.lower().endswith('.jpeg') or img_url.lower().endswith('.png')):
            img_url = urljoin(url, img_url) # Create the full URL for the image
            img_urls.append(img_url)

    download_images_in_batches(img_urls, folder)

def download_images_in_batches(img_urls, folder):
    results = [None] * len(img_urls)  # Initialize a list to store results
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for counter, img_url in enumerate(img_urls, start=1):
            futures.append(executor.submit(download_image, img_url, folder, counter, results))
        
        for future in as_completed(futures):
            future.result()  # Wait for all futures to complete

    # Print the results in order
    if DEBUG:
        for result in results:
            if result:
                print(result)

# Example usage
if __name__ == '__main__':
    website_url = "https://asuracomic.net/series/swordmasters-youngest-son-06d1c859"
    save_folder = "images"
    DEBUG = True
    chptr = get_latest_chapter(website_url)
    if DEBUG:
        print(f"Latest Chapter is {chptr}")
    asyncio.run(scrape_webp_images(website_url+f'/chapter/{chptr}', save_folder))
