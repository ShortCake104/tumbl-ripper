import os
import re
import time

import pytumblr
import requests
from bs4 import BeautifulSoup as bs
from pystyle import *
from tqdm import tqdm
from tumblpy.exceptions import TumblpyError
from urlextract import URLExtract


class TumblrClient():
    def __init__(self, consumer_key, consumer_secret, oauth_token, oauth_secret):
        self.client = pytumblr.TumblrRestClient(consumer_key, consumer_secret, oauth_token, oauth_secret)

    def get(self, endpoint, blog_url, params=None):
        if params is None:
            params = {}
        m = re.match(r"https://(.*)\.tumblr\.com/(.*)", blog_url)
        if m is None:
            return {'meta': {'status': 404, 'msg': 'Not Found'}, 'response': [], 'errors': [{'title': 'Not Found', 'code': 0, 'detail': 'Something flubbed. Try again.'}]}
        else:
            if m.group(1) == "www":
                blog_name = m.group(2)
            else:
                blog_name = m.group(1)
        if endpoint == "posts":
            return self.client.posts(blog_name, **params)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

CONSUMER_KEY = "nrJ1hOSYbWBFMd7QGWdSNW2Trr5A9yDvbmUvizGiskOPNjlcGM"
CONSUMER_SECRET = "v95C36kOWg5Cm4Kq3W3eRFcZwN6j6AJdYagBNiYhrVoOU0dOM1"
OAUTH_TOKEN = '5Fn3JU0mrLbcfiQ7u6aqhfTzRXNOgSVsCwnH0kQOaOj8IQHXYy'
OAUTH_SECRET = 'sTVSisoDxwTyL937SJvAk1cdgR8fiWwQzXOZZUCwt2jhNwvFoL'

client = TumblrClient(CONSUMER_KEY, CONSUMER_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

banner = """
┏┳┓     ┓ ┓  ┳┓•        
 ┃ ┓┏┏┳┓┣┓┃━━┣┫┓┏┓┏┓┏┓┏┓
 ┻ ┗┻┛┗┗┗┛┗  ┛┗┗┣┛┣┛┗ ┛ 
                ┛ ┛     
"""

version = "1.0"

System.Title(f"Tumbl-Ripper v{version}")

if __name__ == "__main__":
    print(Colorate.Vertical(Colors.blue_to_cyan, Center.XCenter(banner), 1))
    while True:
        blog = input("> ")

        print("blog url:", blog)
        try:
            json = client.get("posts", blog_url=blog)
        except TumblpyError:
            if "There was an error making your request.":
                print("RateLimit!")
                input("")
                exit()

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

        offset = 0

        while True:
            posts_ = json["posts"]
            for post in posts_:
                #if post["type"] != "photo":
                #    continue
                post_ = dict()
                post_["id"] = post["id_string"]
                #post["id_string"]
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
            time.sleep(1)
            json = client.get("posts", blog_url=blog, params={"offset": offset})

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
