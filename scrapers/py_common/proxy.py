# common proxy functions
# - set chrome user-agent
# bypassers
# - cloudscraper (pip)
# - flaresolverr/ byparr (external)

# automatic retries with cloudscraper then (flaresolverr/ byparr) if blocked
# caches flaresolverr cookies, userAgent for subsequent requests to same host

import os
import time
import json
import urllib.parse
from pathlib import Path

import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.deps import ensure_requirements

ensure_requirements("requests", "cloudscraper")
import requests
import cloudscraper

class RequestBackend:
  name = "backend"

  @staticmethod
  def is_blocked(res):
    if res.status_code not in (403, 503):
      return False
    body = res.text[:4096].lower()
    return any(marker in body for marker in (
      "cloudflare", "cf-ray", "cf-chl", "challenge-platform",
      "just a moment", "attention required",
    ))

  def request(self, method, url, **kwargs):
    raise NotImplementedError

class RequestsBackend(RequestBackend):
  name = "requests"

  def __init__(self, proxies=None, useragent=None):
    self.session = requests.Session()
    if proxies:
      self.session.proxies = proxies
    if useragent == "inherit":
      ua = get_useragent()
      self.session.headers.update({"User-Agent": ua})
    elif useragent:
      self.session.headers.update({"User-Agent": useragent})

  def _apply_cache(self, url):
    cache_entry = cookie_cache.get(url)
    if cache_entry:
      log.debug(f"[proxy] Using cache for {url}")
      for cookie in cache_entry['cookies']:
        self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'])
      if cache_entry['useragent']:
        self.session.headers.update({"User-Agent": cache_entry['useragent']})
    return bool(cache_entry)

  def request(self, method, url, **kwargs):
    self._apply_cache(url)
    try:
      res = self.session.request(method, url, **kwargs)
      if not self.is_blocked(res):
        return res
      log.warning(f"[proxy] requests blocked ({res.status_code}).")
    except requests.exceptions.RequestException as e:
      log.warning(f"[proxy] Request failed: {e}.")
    raise Exception("Requests backend failed")

class CloudscraperBackend(RequestBackend):
  name = "cloudscraper"

  def __init__(self, proxies=None):
    self.scraper = cloudscraper.create_scraper()
    if proxies:
      self.scraper.proxies = proxies

  def request(self, method, url, **kwargs):
    try:
      res = self.scraper.request(method, url, **kwargs)
      if not self.is_blocked(res):
        return res
      log.warning(f"[proxy] Cloudscraper blocked ({res.status_code}).")
    except requests.exceptions.RequestException as e:
      log.warning(f"[proxy] Cloudscraper request failed: {e}")
    raise Exception("Cloudscraper backend failed")

class FlareSolverrBackend(RequestBackend):
  name = "flaresolverr"

  def request(self, method, url, **kwargs):
    if check_flaresolverr(FLARESOLVERR_URL):
      log.info(f"[proxy] trying FlareSolverr for {url}")
      # HEAD is not supported
      if method == "head":
        method = "get"
        log.warning("[proxy] HEAD not supported by FlareSolverr, using GET instead")
      try:
        post_data = (kwargs.get("json") or kwargs.get("data")) if method == "post" else None
        return flaresolverr_req(url, method=method, postData=post_data, proxy=PROXY_URL)
      except Exception as e:
        log.warning(f"[proxy] FlareSolverr request failed: {e}")
    else:
      raise Exception("FlareSolverr not detected")
    raise Exception("FlareSolverr backend failed")

## END REWRITE

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")

@cache_to_disk(ttl=86400)
def check_flaresolverr(url):
  try:
    requests.get(url, timeout=5)
    log.debug(f"[proxy] FlareSolverr detected at {url}")
    return True
  except requests.exceptions.HTTPError as httperr:
    if httperr.response.status_code == 405:
      log.debug(f"[proxy] FlareSolverr detected at {url}")
      return True
  except requests.exceptions.RequestException:
    log.info(f"[proxy] FlareSolverr not detected at {url}. Requests will be used without bypassing.")
    return False

PROXY_URL = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
if PROXY_URL:
  log.debug(f"[proxy] Proxy detected: {PROXY_URL}")

@cache_to_disk(ttl=86400)
def get_useragent() -> str:
  chrome_ua = requests.get("https://feederbox826.github.io/user-agents/user-agents.json").json()[3]
  return chrome_ua

def flaresolverr_req(url, method="get", postData=None, proxy=None) -> requests.Response:
  if proxy and "@" in proxy:
    log.warning("[proxy] Ignoring unsupported proxy for FlareSolverr")
    proxy = None
  payload = {
    "cmd": f"request.{method}",
    "url": url,
    "proxy": { "url": proxy } if proxy else None
  }
  if postData is not None:
    payload["postData"] = postData
  response = requests.post(FLARESOLVERR_URL, json=payload, timeout=60)
  if response.status_code != 200:
    raise Exception(f"FlareSolverr request failed with status code {response.status_code}: {response.text}")
  solution = response.json().get("solution")
  req_response = requests.Response()
  req_response.status_code = solution.get("status", 200)
  req_response._content = solution.get("response", "").encode("utf-8")
  req_response.headers = solution.get("headers", {})
  req_response.url = solution.get("url", "")
  req_response.request = requests.Request(method, req_response.url, headers=req_response.headers).prepare()
  cookie_cache.set(req_response.url, solution.get("cookies", []), solution.get("userAgent"))
  return req_response

class CookieCache:
  def __init__(self):
    self.cache = {}
    self.cache_file = Path(__file__).parent / "proxy_cache.json"
    if self.cache_file.exists():
      self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
  def get(self, url):
    host = urllib.parse.urlparse(url).netloc
    entry = self.cache.get(host)
    if not entry:
      return None
    expiry = entry.get("expiry")
    if expiry and expiry < time.time():
      log.debug(f"[proxy] cache for {host} expired")
      del self.cache[host]
      self.update()
      return None
    return entry
  def set(self, url, cookies, useragent):
    host = urllib.parse.urlparse(url).netloc
    clearance = next((c for c in cookies if c['name'] == "cf_clearance"), None)
    self.cache[host] = {
      "cookies": cookies,
      "useragent": useragent,
      "expiry": clearance['expiry'] if clearance else None
    }
    self.update()
  def update(self):
    self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")

cookie_cache = CookieCache()

class BackendManager:
  def __init__(self, backends=None):
    proxies = { "http": PROXY_URL, "https": PROXY_URL } if PROXY_URL else {}
    if not backends:
      self.backends = [
        RequestsBackend(proxies=proxies, useragent="inherit"),
        CloudscraperBackend(proxies=proxies),
      ]
      if check_flaresolverr(FLARESOLVERR_URL):
        self.backends.append(FlareSolverrBackend())
    else:
      # populate backends based on name
      backend_classes = {
        "requests": RequestsBackend,
        "cloudscraper": CloudscraperBackend,
        "flaresolverr": FlareSolverrBackend,
      }
      self.backends = []
      for name in backends:
        cls = backend_classes.get(name)
        if cls:
          self.backends.append(cls(proxies=proxies))
        else:
          log.warning(f"[proxy] Unknown backend specified: {name}")

  def request(self, method, url, **kwargs):
    for backend in self.backends:
      try:
        return backend.request(method, url, **kwargs)
      except Exception as e:
        log.debug(f"[proxy] {backend.name} failed: {e}")
    raise Exception("All backends failed")

class StashRequests:
  def __init__ (self, cloudflare=False, useragent="inherit"):
    self.proxies = { "http": PROXY_URL, "https": PROXY_URL } if PROXY_URL else {}
    self.cloudflare = cloudflare
    self.useragent = useragent
    self.manager = BackendManager()

  def get(self, url, **kwargs):
    return self.manager.request("get", url, **kwargs)

  def post(self, url, **kwargs):
    return self.manager.request("post", url, **kwargs)

  def head(self, url, **kwargs):
    return self.manager.request("head", url, **kwargs)

stash_requests = StashRequests()
