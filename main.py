import json
import math
import os
import re
import time
import warnings

import pytumblr
import requests
from bs4 import BeautifulSoup as bs
from PIL import Image, UnidentifiedImageError
from plyer import notification
from pystyle import *
from rich.console import Console
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
from urlextract import URLExtract


class TumblrClient():
    def __init__(self, consumer_key, consumer_secret, oauth_token, oauth_secret):
        self.client = pytumblr.TumblrRestClient(consumer_key, consumer_secret, oauth_token, oauth_secret)

    def get(self, endpoint, blog_url, params=None):
        if params is None:
            params = {}
        m = re.match(r"https://(.*)\.tumblr\.com/(.*)", blog_url)
        if m is None:
            return None
        else:
            if m.group(1) == "www":
                blog_name = m.group(2)
            else:
                blog_name = m.group(1)
        if endpoint == "posts":
            return self.client.posts(blog_name, **params)


def setup():
    keys = ["consumer_key", "consumer_secret", "oauth_token", "oauth_secret"]
    data = {}
    for key in keys:
        while True:
            value = Write.Input(f"[{key.replace('_', ' ').upper()}] > ", Colors.blue_to_cyan, interval=0,
                                hide_cursor=True)
            if value == "":
                continue
            else:
                data[key] = value
                break
    with open("./settings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def settings_load():
    with open("./settings.json", "r", encoding="utf-8") as f:
        settings = json.load(f)

def convert_size(size):
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB")
    i = math.floor(math.log(size, 1024)) if size > 0 else 0
    size = round(size / 1024**i, 2)

    return f"{size} {units[i]}"

def download(posts):
    file_num = 0
    files_size = 0
    def main():
        for post in tqdm(posts, desc="POSTS", leave=False):
            post_id = post["id"]
            urls = post["urls"]
            for url, p in zip(urls, range(len(urls))):
                _, ext = os.path.splitext(url)
                name = f"{post_id}_p{p}{ext}"
                path = os.path.join(img_dir, name)
                if os.path.exists(path):
                    time.sleep(0.01)
                    continue
                while True:
                    with open(path, "wb") as f:
                        try:
                            for chunk in requests.get(url, stream=True).iter_content(chunk_size=1024):
                                f.write(chunk)
                        except Exception as e:
                            time.sleep(1)
                            console.print_exception(extra_lines=5, show_locals=True)
                    try:
                        Image.open(path)
                    except UnidentifiedImageError:
                        time.sleep(1)
                        continue
                    else:
                        file_num = file_num+1
                        break
    main()

os.chdir(os.path.dirname(os.path.abspath(__file__)))
warnings.simplefilter("ignore", category=TqdmExperimentalWarning)

CONSUMER_KEY = "nrJ1hOSYbWBFMd7QGWdSNW2Trr5A9yDvbmUvizGiskOPNjlcGM"
CONSUMER_SECRET = "v95C36kOWg5Cm4Kq3W3eRFcZwN6j6AJdYagBNiYhrVoOU0dOM1"
OAUTH_TOKEN = '5Fn3JU0mrLbcfiQ7u6aqhfTzRXNOgSVsCwnH0kQOaOj8IQHXYy'
OAUTH_SECRET = 'sTVSisoDxwTyL937SJvAk1cdgR8fiWwQzXOZZUCwt2jhNwvFoL'

client = TumblrClient(CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
console = Console()

banner = """
┏┳┓     ┓ ┓  ┳┓•        
 ┃ ┓┏┏┳┓┣┓┃━━┣┫┓┏┓┏┓┏┓┏┓
 ┻ ┗┻┛┗┗┗┛┗  ┛┗┗┣┛┣┛┗ ┛ 
                ┛ ┛     
 
"""

version = "1.1"

System.Title(f"Tumbl-Ripper v{version}")

if __name__ == "__main__":
    System.Clear()
    while True:
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.Center(banner, yspaces=2), 1))
        url = Write.Input(Center.XCenter("[BLOG] > ", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)

        try:
            json = client.get("posts", blog_url=url, params={"limit": 50})
        except Exception as e:
            console.print_exception(extra_lines=5, show_locals=True)
            Write.Input(Center.XCenter("[*] Press ENTER to go back.", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)
            exit()
        else:
            if json is None:
                print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter("[!] ERROR.", spaces=40), 1))
                Write.Input(Center.XCenter("[*] Press ENTER to go back.", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)
                System.Clear()
                continue

        blog_info = json["blog"]
        name = blog_info["name"]
        total_posts = blog_info["total_posts"]
        title = blog_info["title"]
        blog_url = blog_info["url"]
        title_ = title.translate(
            str.maketrans({'\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？', '"': '”', '<': '＜', '>': '＞', '|': '｜'}))
        img_dir = os.path.join("imgs", f"{title_}[{name}]")
        # ブログ名を画像保存フォルダに指定
        print("")
        print(Colorate.Horizontal(Colors.blue_to_cyan,
            Box.Lines(f"NAME: {name}\nTITLE: {title}\nPOSTS: {total_posts}\nURL: {blog_url}"), 1))
        print("")

        if not os.path.exists(img_dir):
            os.mkdir(img_dir)

        posts = list()

        offset = 0

        with console.status("[bold green]Fetching data...") as status:
            while True:
                posts_ = json["posts"]
                for post in posts_:
                    # if post["type"] != "photo":
                    #    continue
                    post_ = dict()
                    post_["id"] = post["id_string"]
                    # post["id_string"]
                    urls = list()
                    if post["type"] == "photo":
                        photos = post["photos"]
                        for photo in photos:
                            img_url = photo["original_size"]["url"]
                            urls.append(img_url)
                    elif post["type"] == "text":
                        soup = bs(post["body"], "lxml")
                        imgs = soup.find_all("img")
                        for img in imgs:
                            try:
                                img_srcset = img["srcset"]
                                extractor = URLExtract()
                                img_urls = extractor.find_urls(img_srcset)
                                img_url = img_urls[-1]
                                urls.append(img_url)
                            except KeyError:
                                img_url = img["src"]
                                urls.append(img_url)
                    post_["urls"] = urls
                    posts.append(post_)
                try:
                    params = json["_links"]["next"]["query_params"]
                except KeyError:
                    break
                offset = offset + len(posts_)
                # time.sleep(1)
                try:
                    json = client.get("posts", blog_url=url, params={"offset": offset, "limit": 50})
                except Exception as e:
                    console.print_exception(extra_lines=5, show_locals=True)
                    Write.Input(Center.XCenter("[*] Press ENTER to go back.", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)
                    System.Clear()
                    break

            print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter("[*] Fetch done.", spaces=40), 1))

        # download
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter("[*] Download started.", spaces=40), 1))

        files_num = 0
        files_size = 0

        start = time.time()
        for post in tqdm(posts, desc="POSTS", leave=False):
            post_id = post["id"]
            urls = post["urls"]
            for url, p in zip(urls, range(len(urls))):
                _, ext = os.path.splitext(url)
                name = f"{post_id}_p{p}{ext}"
                path = os.path.join(img_dir, name)
                if os.path.exists(path):
                    time.sleep(0.01)
                    continue
                while True:
                    with open(path, "wb") as f:
                        try:
                            for chunk in requests.get(url, stream=True).iter_content(chunk_size=1024):
                                f.write(chunk)
                        except Exception as e:
                            time.sleep(1)
                            console.print_exception(extra_lines=5, show_locals=True)
                    try:
                        Image.open(path)
                    except UnidentifiedImageError:
                        time.sleep(1)
                        continue
                    else:
                        files_num = files_num + 1
                        files_size = files_size + 1
                        break
        end = time.time()
        print(Colorate.Horizontal(Colors.blue_to_cyan,
            Box.Lines(f"TIME: {end-start}\nFILES: {files_num}\nSIZE: {convert_size(files_size)}"), 1))

        notification.notify(title="Notice", message="Download finished.", app_name="Tumbl-Ripper", app_icon="./icon.ico")
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter("[*] Download finished.", spaces=40), 1))
        Write.Input(Center.XCenter("[*] Press ENTER to go back.", spaces=40), Colors.blue_to_cyan, interval=0, hide_cursor=True)
        System.Clear()
