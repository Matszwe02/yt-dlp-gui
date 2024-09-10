import time
from concurrent.futures import ThreadPoolExecutor
import requests

start = time.perf_counter()

urls = [
    "https://i.imgur.com/AD3MbBi.jpeg",
    "https://i.imgur.com/zYhkOrM.jpeg",
    "https://i.imgur.com/LRoLTlK.jpeg",
    "https://i.imgur.com/gtWsPu9.jpeg",
    "https://i.imgur.com/jDimNTZ.jpeg",
]

def download_image(url):
    print(f"Downloading {url}")
    resp = requests.get(url)
    with open(url.split("/")[-1], 'wb') as f:
        f.write(resp.content)
    print(f"Done downloading {url}")

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(download_image, urls)

print(f"Total time: {time.perf_counter() - start}")