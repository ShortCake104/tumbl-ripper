import datetime
import json
import math
import os
import re
import shutil
import time
import tomllib
from collections import deque

import pytumblr
import requests
from bs4 import BeautifulSoup as bs
from discord_webhook import DiscordWebhook
from PIL import Image, UnidentifiedImageError
from plyer import notification as notice
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

        def stalker(uuid: str, path: str):
            if not os.path.exists("./stalker.json"):
                stalker = {uuid: path}
                with open("./stalker.json", "w", encoding="utf-8") as f:
                    json.dump(stalker, f, indent=4, ensure_ascii=False)
                return True
            else:
                with open("./stalker.json", "r", encoding="utf-8") as f:
                    stalker = json.load(f)
                if stalker[uuid] == path:
                    return True
                else:
                    old_path = stalker["uuid"]
                    stalker[uuid] = path
                    with open("./stalker.json", "w", encoding="utf-8") as f:
                        json.dump(stalker, f, indent=4, ensure_ascii=False)
                    return old_path

        if qsize := len(self.queue):
            files_num = 0
            files_size = 0
            print_("[*] Download started.")
            notification("Download stared.")
            start = time.time()
            if qsize != 1:
                qbar = tqdm(range(qsize), desc="Queue", leave=False)
            for i in range(qsize):
                post = self.queue.popleft()
                path = os.path.join(settings["directory"], f"{post['title']}[{post['name']}]")
                if result := stalker(post["uuid"], os.path.basename(path)):
                    if not os.path.exists(path):
                        os.makedirs(path, exist_ok=True)
                else:
                    os.rename(os.path.join(settings["directory"], result), path)
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
            info = f"TIME: {datetime.timedelta(seconds=elapsed)}\nFILES: {files_num}\nSIZE: {convert_size(files_size)}"
            print(Colorate.Horizontal(Colors.blue_to_cyan, Box.Lines(info), 1))
            print_("[*] Download finished.")
            notification(f"Download finished.\n{info}")
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
            "uuid": post["blog"]["uuid"],
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
            info = f"NAME: {name}\nTITLE: {title}\nPOSTS: {total_posts}\nURL: {blog_url}"
            print("")
            print(Colorate.Horizontal(Colors.blue_to_cyan,
                Box.Lines(info), 1))
            print("")
            notification(info)
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
                time.sleep(10)
                continue
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

def notification(message: str):
    def desktop(message: str):
        notice.notify(title="Notification", message=message, app_name="Tumbl-Ripper", app_icon="./icon.ico")

    def discord(message: str):
        if settings["notification"]["discord"]["webhookUrl"] != "":
            if settings["notification"]["discord"]["mention"]["enable"] == True:
                if settings["notification"]["discord"]["mention"]["discordId"] != "":
                    message = f"<@{settings['notification']['discord']['mention']['discordId']}>\n{message}"
            DiscordWebhook(url=settings["notification"]["discord"]["webhookUrl"], content=message).execute()

    if settings["notification"]["enable"] == True:
        if settings["notification"]["desktop"]["enable"] == True:
            desktop(message)
        if settings["notification"]["discord"]["enable"] == True:
            discord(message)

def settings():
    with open("settings.toml", "rb") as f:
        settings = tomllib.load(f)
    return settings

banner = """
┏┳┓     ┓ ┓  ┳┓•        
 ┃ ┓┏┏┳┓┣┓┃━━┣┫┓┏┓┏┓┏┓┏┓
 ┻ ┗┻┛┗┗┗┛┗  ┛┗┗┣┛┣┛┗ ┛ 
                ┛ ┛     
 
"""
version = "1.0"
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
    while True:
        System.Clear()
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.Center(banner, yspaces=2), 1))
        url = input_("[RIPPER] > ")

        if m := re.match(r"https://(.*)\.tumblr\.com/(\w*)", url):
            if m.group(1) == "www":
                blog_name = m.group(2)
            else:
                blog_name = m.group(1)
            with console.status("[bold green]Fetching data...") as status:
                    client.user(blog_name)
            print_("[*] Fetch done.")
            client.download()

        input_("[*] Press ENTER to go back.")
