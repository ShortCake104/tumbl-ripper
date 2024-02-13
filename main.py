import datetime
import json
import math
import os
import re
import shutil
import time
from collections import deque

import pytumblr
import requests
from bs4 import BeautifulSoup as bs
from PIL import Image, UnidentifiedImageError
from plyer import notification
from pystyle import *
from requests.exceptions import ChunkedEncodingError
from rich.console import Console
from tqdm import tqdm
from urlextract import URLExtract
from urllib3.exceptions import ProtocolError


class Client:
    def __init__(self, consumer_key, consumer_secret, oauth_token, oauth_secret):
        self.queue = deque()
        self.client = pytumblr.TumblrRestClient(consumer_key, consumer_secret, oauth_token, oauth_secret)

    def download(self):
        def convert_size(size):
            units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB")
            i = math.floor(math.log(size, 1024)) if size > 0 else 0
            size = round(size / 1024 ** i, 2)

            return f"{size} {units[i]}"

        if qsize := len(self.queue):
            files_num = 0
            files_size = 0
            print_("[*] Download started.")
            start = time.time()
            if qsize != 1:
                qbar = tqdm(range(qsize), desc="Queue", leave=False)
            for i in range(qsize):
                post = self.queue.popleft()
                path = os.path.join(settings["directory"], f"{post['title']}[{post['name']}]")
                post_id = post["id"]
                attachments = post["attachments"]
                for attachment, p in zip(tqdm(attachments, desc="Attachments", leave=False), range(len(attachments))):
                    ext = os.path.splitext(attachment)[1]
                    name = f"{post_id}_p{p}{ext}"
                    file = os.path.join(path, name)
                    if os.path.exists(file):
                        continue
                    while True:
                        try:
                            with requests.get(attachment, stream=True) as response:
                                with open(file, "wb") as f:
                                    shutil.copyfileobj(response.raw, f)
                            Image.open(file)
                        except (ProtocolError, UnidentifiedImageError, ChunkedEncodingError, ConnectionError):
                            time.sleep(10)
                        except Exception as e:
                            print(type(e))
                            print(str(e))
                            os.remove(file)
                            input()
                            exit()
                        else:
                            files_num = files_num + 1
                            files_size = files_size + os.path.getsize(file)
                            time.sleep(1)
                            break
                    if "qbar" in locals():
                        qbar.update(1)
            if "qbar" in locals():
                qbar.close()
            elapsed = time.time() - start
            print(Colorate.Horizontal(Colors.blue_to_cyan, Box.Lines
                (f"TIME: {datetime.timedelta(seconds=elapsed)}\nFILES: {files_num}\nSIZE: {convert_size(files_size)}"), 1))
            print_("[*] Download finished.")
        else:
            print_("[!] There is nothing in the queue.")

    def parse(self, post: dict):
        # post["id_string"]
        attachments = list()
        if post["type"] == "photo":
            photos = post["photos"]
            for photo in photos:
                img_url = photo["original_size"]["url"]
                attachments.append(img_url)
        elif post["type"] == "text":
            soup = bs(post["body"], "lxml")
            imgs = soup.find_all("img")
            for img in imgs:
                try:
                    img_srcset = img["srcset"]
                    extractor = URLExtract()
                    img_urls = extractor.find_urls(img_srcset)
                    img_url = img_urls[-1]
                    attachments.append(img_url)
                except KeyError:
                    img_url = img["src"]
                    attachments.append(img_url)
        post_ = {
            "name": post["blog"]["name"],
            "title": post["blog"]["title"].translate(str.maketrans(
                {'\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？', '"': '”', '<': '＜', '>': '＞', '|': '｜'})
            ),
            "id": post["id_string"],
            "attachments": attachments
        }
        self.queue.append(post_)

    def user(self, blog_name: str):
        try:
            blog_info = self.client.blog_info(blog_name)["blog"]
        except KeyError:
            print_("[!] Not found.")
            return
        else:
            name = blog_info["name"]
            total_posts = blog_info["total_posts"]
            title = blog_info["title"]
            blog_url = blog_info["url"]
            print("")
            print(Colorate.Horizontal(Colors.blue_to_cyan,
                Box.Lines(f"NAME: {name}\nTITLE: {title}\nPOSTS: {total_posts}\nURL: {blog_url}"), 1))
            print("")
        offset = 0
        while True:
            data = self.client.posts(blog_name, "photo", offset=offset, limit=50)
            try:
                posts = data["posts"]
            except KeyError:
                """
                example:
                {'meta': {'status': 404, 'msg': 'Not Found'}, 'response': [], 
                'errors': [{'title': 'Not Found', 'code': 0, 'detail': 'Internet strangeness. Try again.'}]}
                """
                break
            for post in posts:
                self.parse(post)
            offset = offset + len(posts)
            try:
                data["_links"]["next"]["query_params"]
            except KeyError:
                break


def print_(text: str):
    print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter(text, spaces=40), 1))


def input_(text: str):
    return Write.Input(Center.XCenter(text, spaces=40), Colors.blue_to_cyan,
                       interval=0, hide_cursor=True)

def settings():
    with open("settings.json", "r") as f:
        settings = json.load(f)
    return settings

banner = """
┏┳┓     ┓ ┓  ┳┓•        
 ┃ ┓┏┏┳┓┣┓┃━━┣┫┓┏┓┏┓┏┓┏┓
 ┻ ┗┻┛┗┗┗┛┗  ┛┗┗┣┛┣┛┗ ┛ 
                ┛ ┛     
 
"""

version = "1.1"

System.Title(f"Tumbl-Ripper v{version}")

os.chdir(os.path.dirname(os.path.abspath(__file__)))
settings = settings()

CONSUMER_KEY = settings["auth"]["consumer_key"]
CONSUMER_SECRET = settings["auth"]["consumer_secret"]
OAUTH_TOKEN = settings["auth"]["oauth_token"]
OAUTH_SECRET = settings["auth"]["oauth_secret"]

client = Client(CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
console = Console()

if __name__ == "__main__":
    System.Clear()
    while True:
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.Center(banner, yspaces=2), 1))
        url = Write.Input(Center.XCenter("[RIPPER] > ", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)

        if m := re.match(r"https://(.*)\.tumblr\.com/(\w*)", url):
            if m.group(1) == "www":
                blog_name = m.group(2)
            else:
                blog_name = m.group(1)
            with console.status("[bold green]Fetching data...") as status:
                    client.user(blog_name)
            print_("[*] Fetch done.")
            client.download()
            notification.notify(title="Notice", message="Download finished.", app_name="Tumbl-Ripper", app_icon="./icon.ico")

        Write.Input(Center.XCenter("[*] Press ENTER to go back.", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)
        System.Clear()
