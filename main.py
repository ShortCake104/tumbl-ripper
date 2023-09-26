import os
import pprint
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging import (DEBUG, INFO, FileHandler, Formatter, StreamHandler,
                     getLogger)
from threading import Thread
from webbrowser import open_new

import requests
from bs4 import BeautifulSoup as bs
from tqdm import tqdm
from tumblpy import Tumblpy
from urlextract import URLExtract


def make_logger(name):
    logger = getLogger(name)
    logger.setLevel(DEBUG)

    st_handler = StreamHandler()
    st_handler.setLevel(INFO)
    st_handler.setFormatter(Formatter("[{levelname}] {message}", style="{"))
    logger.addHandler(st_handler)

    fl_handler = FileHandler(filename=".log", encoding="utf-8", mode="w")
    fl_handler.setLevel(DEBUG)
    fl_handler.setFormatter(
        Formatter(
            "[{levelname}] {asctime} [{filename}:{lineno}] {message}", style="{"
        )
    )
    logger.addHandler(fl_handler)

    return logger

class OAuthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        global oauth_verifier
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            oauth_verifier = query["oauth_verifier"][0]
            response = f"Successfully!\nAuthorization Code: {oauth_verifier}"
            print(response)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(bytes(response, encoding="utf-8"))
            Thread(target=httpd.shutdown, daemon=True).start()
        except KeyError:
            logger.error("error")
            logger.error(self.path)

logger = make_logger(__name__)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CONSUMER_KEY = "your consumer key"
CONSUMER_SECRET = "your consumer secret key"

t = Tumblpy(CONSUMER_KEY, CONSUMER_SECRET)

auth_props = t.get_authentication_tokens()
auth_url = auth_props["auth_url"]
#example https://siyomato.tumblr.com/?oauth_token=UQ3CcKnCxbbPO7VnsNHvhxvIGexYYcqWIFrxOK7ySTfXGKDO2q&oauth_verifier=6ttfXTuj3SUeNUhhtizKbbcSV0BbuA6HgH2M4hOisr5HfFN1PR

OAUTH_TOKEN = auth_props["oauth_token"]
OAUTH_TOKEN_SECRET = auth_props["oauth_token_secret"]
oauth_verifier = None

print(auth_url)
print(OAUTH_TOKEN)
print(OAUTH_TOKEN_SECRET)

open_new(auth_url)

httpd = HTTPServer(("localhost", 8000), OAuthServer)
httpd.serve_forever()

t = Tumblpy(CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

print(oauth_verifier)
authorized_tokens = t.get_authorized_tokens(oauth_verifier)

oauth_token = authorized_tokens["oauth_token"]
oauth_token_secret = authorized_tokens["oauth_token_secret"]

print(oauth_token)
print(oauth_token_secret)

if __name__ == "__main__":
    while True:
        blog = input("> ")

        print("blog url:", blog)

        json = t.get("posts", blog_url=blog)

        blog_info = json["blog"]
        name = blog_info["name"]
        total_posts = blog_info["total_posts"]
        title = blog_info["title"]
        dir = os.path.join("imgs", title)
        # ブログ名を画像保存フォルダに指定
        print(f"name: {name}\ntitle: {title}\ntotal posts: {total_posts}")

        if not os.path.exists(dir):
            os.mkdir(dir)

        posts = list()

        #pprint.pprint(json)
        #exit()

        while True:
            posts_ = json["posts"]
            for post in posts_:
                #if post["type"] != "photo":
                #    continue
                post_ = dict()
                post_["id"] = post["id_string"]
                post["id_string"]
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
            time.sleep(1)
            json = t.get("posts", blog_url=blog, params=params)

        # download
        print("download started.")
        for post in tqdm(posts, desc="Posts"):
            post_id = post["id"]
            urls = post["urls"]
            for url, p in zip(tqdm(urls, desc="Images", leave=False), range(len(urls))):
                _, ext = os.path.splitext(url)
                name = f"{post_id}_p{p}{ext}"
                path = os.path.join(dir, name)
                if os.path.exists(path):
                    continue
                with open(path, "wb") as f:
                    try:
                        for chunk in requests.get(url, stream=True).iter_content(chunk_size=1024):
                            f.write(chunk)
                    except Exception as e:
                        time.sleep(1)
                        print(e)
                time.sleep(1)
                # sleep挟まないと何故か正しくダウンロードできずにファイルが壊れる
        print("download finished.")
