import os
import zipfile
from scrape import scrape_webp_images, get_latest_chapter
import random, string

def create_cbz(images_folder, output_cbz):
    # Create a ZipFile object with store compression method
    with zipfile.ZipFile(output_cbz, 'w', zipfile.ZIP_STORED) as cbz:
        # Loop through all files in the images folder
        for root, _, files in os.walk(images_folder):
            for file in sorted(files):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # Create the full file path
                    file_path = os.path.join(root, file)
                    # Add the file to the CBZ archive
                    cbz.write(file_path, arcname=file)
    print(f"CBZ file created: {output_cbz}")

def random_string(length: int) -> str:
    """Generate a random string of fixed `length`"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

async def getCBZ(url: str, chapter: int | str, name: str) -> str:

    image_folder = 'images'

    if chapter == 'latest':
        chapter = get_latest_chapter(url)

    scrape_webp_images(url + '/chapter/' + str(chapter), image_folder)
    cbz_name = '[' + str(chapter) + '] ' + name + '.cbz'
    create_cbz(image_folder, cbz_name)

    # remove images
    for root, _, files in os.walk(image_folder):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
    # os.rmdir(image_folder)
    
    return cbz_name
