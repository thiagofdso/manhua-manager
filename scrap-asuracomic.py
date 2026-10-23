import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
from io import BytesIO

def extract_series_name(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    series_name = next((part for part in path_parts if '-' in part), None)
    return series_name

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_and_convert_image(url, path):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Abrir a imagem WebP
        img = Image.open(BytesIO(response.content))
        
        # Converter e salvar como JPG
        img = img.convert("RGB")
        img.save(path, "JPEG")
        
        print(f"Downloaded and converted: {path}")
    except requests.RequestException as e:
        print(f"Failed to download: {url}. Error: {e}")
    except Exception as e:
        print(f"Failed to convert image: {url}. Error: {e}")

def download_image(url, path):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(path, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded: {path}")
    except requests.RequestException as e:
        print(f"Failed to download: {url}. Error: {e}")

def scrape_chapter(driver, url, series_dir, chapter_id):
    chapter_dir = os.path.join(series_dir, f"chapter_{chapter_id:03d}")
    
    # Verifica se o diretório do capítulo já existe
    if os.path.exists(chapter_dir):
        print(f"Chapter {chapter_id:03d} already exists. Skipping.")
        return

    driver.set_page_load_timeout(15)
    try:
        selector = r"body > div.max-w-\[1220px\].pt-2 > div > div > div > div.py-8.-mx-5.md\:mx-0.flex.flex-col.items-center.justify-center"
        print("selector:\n", selector)
        driver.get(url)
        #time.sleep(10)
        #
        #WebDriverWait(driver, 20).until(
        #    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        #)
    except Exception as e:
        driver.execute_script("window.stop();")
        #print(f"Failed to load chapter {chapter_id}. Error: {e}")
        #return
    # Restaura o timeout padrão
    driver.set_page_load_timeout(30)

    image_container = driver.find_element(By.CSS_SELECTOR, selector)
    
    if not image_container:
        print(f"No image container found for chapter {chapter_id:03d}")
        return
    print("Container de imagem encontrado")

    create_directory(chapter_dir)

    images = image_container.find_elements(By.TAG_NAME, 'img')
    for index, img in enumerate(images, start=1):
        image_url = img.get_attribute('src')
        if image_url:
            image_filename = f"page_{index:03d}.jpg"
            image_path = os.path.join(chapter_dir, image_filename)
            download_and_convert_image(image_url, image_path)
        else:
            print(f"No src attribute found for image {index} in chapter {chapter_id}")

    time.sleep(2)  # Add a delay between chapters to avoid overwhelming the server
    
def main():
    base_url = "https://asuracomic.net/series/the-extras-academy-survival-guide-507d5735/chapter/{chapterid}"
    #series_name = extract_series_name(base_url)
    series_name = "the-extras-academy-survival-guide"
    if not series_name:
        print("Failed to extract series name from URL")
        return

    start_chapter = 56
    end_chapter = 56

    series_dir = os.path.join(os.getcwd(), series_name)
    create_directory(series_dir)

    chrome_options = Options()
    chrome_options.add_argument("--headless")     
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--enable-javascript")

    # Especificar o caminho do perfil do Chrome
    #user_profile = "C:\\Users\\thiag\\AppData\\Local\\Google\\Chrome\\User Data\\Default"  # Substitua pelo caminho correto no seu sistema
    #chrome_options.add_argument(f"user-data-dir={user_profile}")

    # Caminho para o ChromeDriver
    chrome_driver_path = r"C:\Users\thiag\\Documents\scraping\chromedriver-win64\chromedriver.exe" 

    driver = uc.Chrome(options=chrome_options, driver_executable_path=chrome_driver_path,version_main=133)

    try:
        for chapter_id in range(start_chapter, end_chapter + 1):
            chapter_url = base_url.format(chapterid=chapter_id)
            print(f"Scraping chapter {chapter_id}")
            scrape_chapter(driver, chapter_url, series_dir, chapter_id)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()