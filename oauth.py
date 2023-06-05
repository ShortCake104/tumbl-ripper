from oauthlib.oauth2 import WebApplicationClient
from http.server import HTTPServer, BaseHTTPRequestHandler
from webbrowser import open_new
import urllib.request
from urllib.parse import urlparse, parse_qs
import json
import threading

class OAuthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        auth_path = self.path
        parsed_path = urlparse(auth_path)
        query = parse_qs(parsed_path.query)
        auth_code = query["code"][0]
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(bytes(f"Successfully!\nAuthorization Code: {auth_code}", encoding="utf-8"))
        threading.Thread(target=httpd.shutdown, daemon=True).start()


def main():
    oauth = WebApplicationClient(CONSUMER_KEY)

    url, headers, body = oauth.prepare_authorization_request('https://www.tumblr.com/oauth2/authorize', redirect_url=REDIRECT_URL, scope=SCOPE)
    open_new(url)

    httpd.serve_forever()

    url = "https://api.tumblr.com/v2/oauth2/token"
    header = {'Content-Type': 'application/x-www-form-urlencoded'}
    body = f"grant_type=authorization_code&code={auth_code}&client_id={CONSUMER_KEY}&client_secret={CONSUMER_SECRET}&redirect_uri={REDIRECT_URL}"
    req = urllib.request.Request(url, body.encode(), headers=headers)
    with urllib.request.urlopen(req) as res:
        oauth.parse_request_body_response(res.read())

    print(f"refresh token: {oauth.refresh_token}")



CONSUMER_KEY = ''
CONSUMER_SECRET = ''
SCOPE = ["basic", "write", "offline_access"]
REDIRECT_URL = "http://localhost:8000/"

httpd = HTTPServer(("localhost", 8000), OAuthServer)
auth_path = None
auth_code = None

if __name__ == "__main__":
    main()
