#!/usr/bin/env python3
"""
CS2 Lineup Viewer
==================
A small desktop app: pick a map, a side (T/CT), and a nade type, click a
lineup in the list, and it shows the actual cover image + throw info
(stand spot, aim point, throw technique, difficulty, and a console
setpos/setang command you can paste in a practice server) pulled live
from cs2util.com.

This is NOT a bundled/offline database — every run fetches current data
from the web, so it stays in sync with that site's lineups. That also
means it depends on cs2util.com staying online and keeping its page
structure roughly the same; the parsing below is written defensively
(regex over the page's text content rather than brittle CSS selectors)
but a redesign on their end could still break it. If it does, the
LIST_SELECTORS / detail-page regexes near the top are the place to fix.

Setup:
    pip install requests beautifulsoup4 pillow

Run:
    python cs2_lineups.py

Notes:
- First load for a given map/nade-type takes a few seconds (it has to
  open every lineup's detail page once to read which side it's for and
  cache the result). After that it's instant — results are cached to
  ./cs2_lineup_cache/ as JSON + the cover images as files.
- Only fetches from cs2util.com, at a light pace (small delay between
  requests) and identifies itself with a normal browser user-agent for
  compatibility. For personal, occasional use. If you'd rather not hit
  their servers at all, delete the cache folder to reset, or just
  browse the site directly.
- The "Console Command" shown (setpos/setang) only works with
  sv_cheats 1 on a local/practice server — it teleports you to the
  exact throw spot so you can drill the lineup. It does nothing in a
  real matchmaking/Premier game.
"""

import json
import os
import re
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from io import BytesIO
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    raise SystemExit(
        "Missing dependency. Run:\n    pip install requests beautifulsoup4 pillow"
    )

try:
    import imageio
    VIDEO_PLAYBACK_AVAILABLE = True
except ImportError:
    # In-app video playback is optional — everything else works without
    # it, so this doesn't raise SystemExit like the PIL import above.
    # Missing this just means the "Watch video" button falls back to
    # opening the clip in a browser tab instead of playing it inline.
    VIDEO_PLAYBACK_AVAILABLE = False

BASE = "https://www.cs2util.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
REQUEST_DELAY = 0.15  # seconds between requests, be polite

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cs2_lineup_cache")
IMG_CACHE_DIR = os.path.join(CACHE_DIR, "images")
VIDEO_CACHE_DIR = os.path.join(CACHE_DIR, "videos")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(IMG_CACHE_DIR, exist_ok=True)
os.makedirs(VIDEO_CACHE_DIR, exist_ok=True)

FAVORITES_PATH = os.path.join(CACHE_DIR, "favorites.json")


def load_favorites():
    """Favorited lineups, keyed by their (unique, stable) URL. Returns an
    empty set on any read problem — favorites are a convenience feature,
    never worth crashing the app over."""
    try:
        with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data)
    except (OSError, json.JSONDecodeError):
        pass
    return set()


def save_favorites(favorites_set):
    try:
        with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(favorites_set), f, indent=2)
    except OSError:
        pass  # non-critical — the star just won't persist to next launch

MAPS = ["dust2", "mirage", "inferno", "nuke", "ancient", "train",
        "cache", "anubis", "overpass", "vertigo"]
MAP_LABELS = {
    "dust2": "Dust 2", "mirage": "Mirage", "inferno": "Inferno", "nuke": "Nuke",
    "ancient": "Ancient", "train": "Train", "cache": "Cache", "anubis": "Anubis",
    "overpass": "Overpass", "vertigo": "Vertigo",
}
MAP_KEY_BY_LABEL = {v: k for k, v in MAP_LABELS.items()}  # reverse lookup for the dropdown's displayed value
NADE_TYPES = {"Smoke": "smoke", "Flash": "flash", "Molotov": "molotov", "HE Grenade": "grenade"}
SIDES = ["All", "T", "CT"]

session = requests.Session()
session.headers.update(HEADERS)


def _get(url, retries=2):
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=12)
            r.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return r.text
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(0.5)


CACHE_FORMAT_VERSION = 5  # bumped: added "video" field to each item


def _cache_path(map_key, nade_key):
    return os.path.join(CACHE_DIR, f"{map_key}_{nade_key}.json")


def _slug_name(href):
    """Decode any %-encoded characters in the URL slug, then title-case it."""
    slug = unquote(href.rstrip("/").split("/")[-1])
    return slug.replace("-", " ").replace("_", " ").title()


def _clean_name(raw_name, href, area="Lineup", counter=0):
    """Normalize a lineup's display name: fix known site typos, replace
    non-Latin names with a readable fallback, and capitalize acronyms
    (T/CT/A/B) consistently. Tries, in order: the visible name → the
    URL slug (decoded) → a guaranteed-readable synthetic label, so the
    result is always plain, readable ASCII even if the site's own name
    and URL are both in a non-Latin script."""
    name = raw_name
    if not name or re.search(r"[^\x00-\x7F]", name):
        name = _slug_name(href)
    if not name or re.search(r"[^\x00-\x7F]", name):
        # even the decoded slug is non-Latin — nothing readable exists
        # for this lineup anywhere on the page, so label it predictably
        # instead of showing garbled or foreign text
        name = f"{area} Lineup #{counter}"

    name = re.sub(r"\bsomke\b", "Smoke", name, flags=re.I)
    name = re.sub(r"\bmolitov\b", "Molotov", name, flags=re.I)

    def fix_word(w):
        bare = w.strip(".,")
        if bare.upper() in ("CT", "T", "A", "B"):
            return w.upper()
        return w
    name = " ".join(fix_word(w) for w in name.split())
    return name.strip()


def fetch_listing(map_key, nade_key):
    """Return list of dicts: {name, url, area} for every lineup on this
    map/nade page. 'area' comes from the section heading each lineup sits
    under on the page (Outside, A Site, Squeaky, etc.)."""
    html = _get(f"{BASE}/{map_key}/{nade_key}")
    soup = BeautifulSoup(html, "html.parser")
    prefix = f"/{map_key}/{nade_key}/"
    area_pattern = re.compile(rf"^{re.escape(map_key)}\s+(.+?)\s+\S+$", re.I)

    seen, items = set(), []
    current_area = "Other"
    area_counters = {}
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "a"]):
        if tag.name != "a":
            m = area_pattern.match(tag.get_text(strip=True))
            if m:
                current_area = m.group(1).strip().title()
            continue
        href = tag.get("href")
        if not href or not href.startswith(prefix) or href in seen:
            continue
        seen.add(href)
        area_counters[current_area] = area_counters.get(current_area, 0) + 1
        name = _clean_name(tag.get_text(strip=True), href, area=current_area,
                            counter=area_counters[current_area])
        items.append({"name": name, "url": BASE + href, "area": current_area})
    return items


LABELS = {
    "team": re.compile(r"\b(smoke|flash|molotov|grenade)\s*\n*\s*(t|ct)\b", re.I),
    "area": None,  # grabbed positionally, see parse_detail
    "difficulty": re.compile(r"Difficulty\s+(Easy|Medium|Hard)", re.I),
    "air_time": re.compile(r"Air Time\s+([\d.]+)", re.I),
    "jump_throw": re.compile(r"Jump Throw\s+(Yes|No)", re.I),
    "movement": re.compile(r"Movement\s+([A-Za-z ]+?)(?:\n|Difficulty)", re.I),
    "mouse": re.compile(r"Mouse Button\s+([A-Za-z ]+?Click)", re.I),
    "console": re.compile(r"Console Command\s+(setpos[^\n]+)", re.I),
}


def parse_detail(url):
    """Fetch one lineup's detail page and pull out everything useful."""
    html = _get(url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    data = {"url": url, "image": None, "video": None, "team": None, "difficulty": None,
            "air_time": None, "jump_throw": None, "movement": None,
            "mouse": None, "console": None, "steps": None, "usage": None}

    m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if not m:
        m = re.search(r'name="twitter:image"\s+content="([^"]+)"', html)
    if m:
        data["image"] = m.group(1)
        # The site's demo video lives at the exact same path as the cover
        # image, just without "-cover" and with a .webm extension instead
        # of .webp — confirmed against two real pages before relying on
        # this rather than assumed. Falls back to None (no video button
        # shown) if a given image doesn't follow that pattern.
        if data["image"].endswith("-cover.webp"):
            data["video"] = data["image"][: -len("-cover.webp")] + ".webm"

    m = LABELS["team"].search(text)
    if m:
        data["team"] = m.group(2).upper()

    for key in ("difficulty", "air_time", "jump_throw", "movement", "mouse", "console"):
        m = LABELS[key].search(text)
        if m:
            data[key] = m.group(1).strip()

    m = re.search(r"Lineup\s*&\s*Steps\s*\n(.*?)(?:\n##|\nUsage Scenarios|\nRelated Nades|$)",
                  text, re.S)
    if m:
        data["steps"] = m.group(1).strip()[:800]

    m = re.search(r"Usage Scenarios\s*\n(.*?)(?:\n##|\nRelated Nades|\nComments|$)",
                  text, re.S)
    if m:
        data["usage"] = m.group(1).strip()[:800]

    return data


def _has_useful_content(item):
    """An entry is worth keeping only if it has an image or some written
    guidance — a bare name with nothing else isn't usable mid-match."""
    return bool(item.get("image") or item.get("steps") or item.get("usage"))


def load_lineups(map_key, nade_key, progress_cb=None):
    """Listing + per-item detail, cached to disk. Entries with no image and
    no written steps/usage are dropped — nothing to show for them.
    progress_cb(done, total). Returns (items, failed_count) — failed_count
    is how many detail pages threw an exception while fetching/parsing
    (network hiccup, unexpected page structure, etc.); those items are
    silently missing from the results otherwise, so the caller can surface
    this instead of the user just seeing a slightly-smaller-than-expected
    list with no explanation."""
    cpath = _cache_path(map_key, nade_key)
    if os.path.exists(cpath):
        with open(cpath, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if isinstance(cached, dict) and cached.get("_cache_format") == CACHE_FORMAT_VERSION:
            return cached["items"], cached.get("_failed_count", 0)
        # old-format cache (predates area/name-cleanup/empty-filtering) — refetch

    items = fetch_listing(map_key, nade_key)
    total = len(items)
    kept = []
    failed_count = 0
    for i, item in enumerate(items):
        try:
            detail = parse_detail(item["url"])
        except Exception:
            detail = {}
            failed_count += 1
        item.update(detail)
        if _has_useful_content(item):
            kept.append(item)
        if progress_cb:
            progress_cb(i + 1, total)

    with open(cpath, "w", encoding="utf-8") as f:
        json.dump({"_cache_format": CACHE_FORMAT_VERSION, "items": kept,
                    "_failed_count": failed_count}, f, indent=2)
    return kept, failed_count


def _mark_dot_near(img, draw, cx, cy, search_r, marker_r):
    """Look for a green-dominant dot within search_r of (cx, cy); if found,
    redraw it as a bigger, outlined, saturated marker. Returns True if a
    dot was found and marked."""
    w, h = img.size
    x0, y0 = max(0, cx - search_r), max(0, cy - search_r)
    x1, y1 = min(w, cx + search_r), min(h, cy + search_r)
    roi = img.crop((x0, y0, x1, y1))
    px = roi.load()
    matches = []
    for yy in range(roi.height):
        for xx in range(roi.width):
            r, g, b = px[xx, yy]
            if g > r + 25 and g > b + 15 and g > 100:
                matches.append((xx, yy))
    if not matches:
        return False

    mx = sum(p[0] for p in matches) / len(matches)
    my = sum(p[1] for p in matches) / len(matches)
    dot_x = int(x0 + mx)
    dot_y = int(y0 + my)

    draw.ellipse((dot_x - marker_r, dot_y - marker_r, dot_x + marker_r, dot_y + marker_r),
                  fill=(230, 30, 30))
    return True


def _enhance_crosshair(img):
    """CS2's in-game crosshair renders as a small dot dead-center of the
    player's view (the camera rotates, the crosshair never moves). It's
    often a pale green that all but disappears against a similarly-toned
    background like blue sky.

    cs2util's cover images are side-by-side composites — a "where to aim"
    panel and a "where it lands" panel, each a separate screenshot with
    its OWN crosshair at the center of that half. The center of the whole
    composite image is just the seam between them, so this checks the
    center of the left half and the center of the right half separately,
    rather than the center of the full image."""
    try:
        w, h = img.size
        draw = ImageDraw.Draw(img)
        search_r = max(12, min(w // 2, h) // 20)
        marker_r = max(2, min(w, h) // 160)
        found_any = False
        for half_cx in (w // 4, (3 * w) // 4):  # left-half center, right-half center
            if _mark_dot_near(img, draw, half_cx, h // 2, search_r, marker_r):
                found_any = True
        if not found_any:
            # fall back to the whole-image center, in case a future image
            # isn't actually a two-panel composite
            _mark_dot_near(img, draw, w // 2, h // 2, search_r, marker_r)
        return img
    except Exception:
        return img  # cosmetic enhancement only — never let it break image loading


def get_image(url):
    """Download (or read from disk cache) a cover image, return PIL Image
    with the crosshair dot contrast-boosted for visibility."""
    fname = re.sub(r"[^a-zA-Z0-9]+", "_", url)[-120:] + ".img"
    fpath = os.path.join(IMG_CACHE_DIR, fname)
    if os.path.exists(fpath):
        with open(fpath, "rb") as f:
            raw = f.read()
    else:
        r = session.get(url, timeout=12)
        r.raise_for_status()
        raw = r.content
        with open(fpath, "wb") as f:
            f.write(raw)
        time.sleep(REQUEST_DELAY)
    img = Image.open(BytesIO(raw)).convert("RGB")
    return _enhance_crosshair(img)


def get_video_path(url):
    """Download (or read from disk cache) a lineup's demo clip, return the
    on-disk file path (imageio's ffmpeg backend reads from a real file,
    not bytes in memory — fine here since clips are only a few MB)."""
    fname = re.sub(r"[^a-zA-Z0-9]+", "_", url)[-120:] + ".webm"
    fpath = os.path.join(VIDEO_CACHE_DIR, fname)
    if os.path.exists(fpath):
        return fpath
    r = session.get(url, timeout=20)
    r.raise_for_status()
    with open(fpath, "wb") as f:
        f.write(r.content)
    time.sleep(REQUEST_DELAY)
    return fpath


# ---------------------------------------------------------------- UI ----

TEAM_COLOR = {"T": "#e8a23a", "CT": "#5aa9e6"}
DIFF_COLOR = {"Easy": "#7fc76b", "Medium": "#e8c33a", "Hard": "#e0602f"}

# Map calibration data (per-map zone boxes, callout label positions,
# and the real-setpos coordinate conversions) lives in its own module —
# see calibration_data.py for the full explanation and accuracy notes.
# It's pure data plus two small matching functions, no Tkinter or
# network dependency, and was pulled out here because it had grown to
# over 600 lines on its own.
from calibration_data import (
    MAP_ZONE_LAYOUT, CALLOUT_POINTS, MAP_CALIBRATION, MAP_IMAGE_REGIONS,
    _guess_callout_pins, _setpos_stand_point,
)

# Optional real map images: drop a file named {map_key}.png/.jpg/.webp into
# this folder (next to the script) and the zone canvas will use it as the
# background instead of the plain schematic, with the same clickable
# regions overlaid. Nothing here is ever downloaded automatically — these
# are only used if you put a file there yourself.
MAP_IMG_DIR = os.path.join(SCRIPT_DIR, "map_images")
os.makedirs(MAP_IMG_DIR, exist_ok=True)


def _find_map_image(map_key):
    """Return the path to a locally-supplied background image for this
    map, or None if the user hasn't dropped one into map_images/."""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(MAP_IMG_DIR, map_key + ext)
        if os.path.exists(p):
            return p
    return None


class LineupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CS2 Lineup Viewer - By Milo")
        self.geometry("1100x700+40+40")
        self.resizable(False, False)  # fixed by default — the "Lock window size" checkbox toggles this
        self.minsize(900, 600)  # only matters once unlocked, so resizing can't break the layout
        self.configure(bg="#12161a")
        self._photo = None  # keep a reference so tkinter doesn't GC it
        self._image_request_id = 0  # bumped on every selection; lets a slow/stale image load detect it's outdated and discard itself
        self._video_playing = False
        self._video_playback_id = 0  # bumped whenever playback starts/stops/switches; a stale load or frame-timer checks this before touching the UI
        self._video_after_id = None  # the scheduled self.after() call for the next frame, so it can be cancelled
        self._video_photo_frames = None
        self._video_fps = 24
        self._video_url = None  # which clip is currently playing/loaded, so re-clicking the same chip toggles off rather than restarting
        self.video_chip = None  # the "Watch video" badge, set once _on_select first creates it
        self._items = []
        self._nuke_level = "outside"  # "outside" (Outside/Main/Squeaky/A Site/Ramp) or "inside" (B Site)
        self._highlight_area = None  # which zone the map highlights — follows the selected lineup, not just the Area filter
        self._name_pins = []  # precise (label, rel_x, rel_y) pins guessed from the selected lineup's name
        self._current_map_key = None  # set once a map is first loaded; guards the resize handler before then
        self._favorites = load_favorites()  # set of favorited lineup URLs, persisted across launches
        self._current_item = None  # the lineup currently shown in the right panel, for the favorite-star toggle
        self._build()

    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        BG = "#12161a"
        PANEL = "#171b1c"
        TOOLBAR = "#181d21"
        BORDER = "#2a3132"
        TEXT = "#e8ecec"
        MUTED = "#6b7677"
        ACCENT = "#e8a23a"

        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 19))

        style.configure("Toolbar.TFrame", background=TOOLBAR)
        style.configure("Toolbar.TLabel", background=TOOLBAR, foreground=MUTED, font=("Segoe UI", 10))

        style.configure("TButton", font=("Segoe UI", 10), padding=5,
                         background=PANEL, foreground=TEXT, bordercolor=BORDER,
                         focuscolor=PANEL, relief="flat")
        style.map("TButton", background=[("active", "#232a2b"), ("disabled", PANEL)],
                   foreground=[("disabled", MUTED)])
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=6,
                         background=ACCENT, foreground="#12161a", bordercolor=ACCENT,
                         focuscolor=ACCENT, relief="flat")
        style.map("Accent.TButton", background=[("active", "#f0af52"), ("disabled", "#4a3a1e")],
                   foreground=[("disabled", "#8a7550")])

        style.configure("TCombobox", fieldbackground=PANEL, background=TOOLBAR,
                         foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                         lightcolor=PANEL, darkcolor=PANEL, padding=4)
        style.map("TCombobox",
                   fieldbackground=[("readonly", PANEL), ("disabled", PANEL)],
                   foreground=[("readonly", TEXT)],
                   background=[("readonly", TOOLBAR)],
                   bordercolor=[("focus", ACCENT)])
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", "#12161a")
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

        style.configure("TCheckbutton", background=TOOLBAR, foreground=TEXT, focuscolor=TOOLBAR)
        style.map("TCheckbutton", background=[("active", TOOLBAR)],
                   indicatorcolor=[("selected", ACCENT), ("!selected", BORDER)])

        style.configure("TScrollbar", background=PANEL, troughcolor=BG, bordercolor=BG,
                         arrowcolor=MUTED)

        top = tk.Frame(self, bg="#181d21")
        top.pack(side="top", fill="x")
        top_inner = ttk.Frame(top, style="Toolbar.TFrame", padding=(14, 12, 14, 10))
        top_inner.pack(side="top", fill="x")
        top = top_inner  # everything below still refers to `top`

        ttk.Label(top, text="Map", style="Toolbar.TLabel").grid(row=0, column=0, padx=(0, 4), pady=2, sticky="w")
        self.map_var = tk.StringVar(value=MAP_LABELS[MAPS[0]])
        map_box = ttk.Combobox(top, textvariable=self.map_var, state="readonly",
                                values=[MAP_LABELS[m] for m in MAPS], width=12)
        map_box.current(0)
        map_box.grid(row=0, column=1, padx=(0, 14), pady=2)

        ttk.Label(top, text="Type", style="Toolbar.TLabel").grid(row=0, column=2, padx=(0, 4), pady=2, sticky="w")
        self.nade_var = tk.StringVar(value="Smoke")
        nade_box = ttk.Combobox(top, textvariable=self.nade_var, state="readonly",
                                 values=list(NADE_TYPES.keys()), width=10)
        nade_box.current(0)
        nade_box.grid(row=0, column=3, padx=(0, 14), pady=2)

        ttk.Label(top, text="Side", style="Toolbar.TLabel").grid(row=0, column=4, padx=(0, 4), pady=2, sticky="w")
        self.side_var = tk.StringVar(value="All")
        side_box = ttk.Combobox(top, textvariable=self.side_var, state="readonly",
                                 values=SIDES, width=5)
        side_box.current(0)
        side_box.grid(row=0, column=5, padx=(0, 14), pady=2)
        side_box.bind("<<ComboboxSelected>>", lambda e: self._refresh_list())

        ttk.Label(top, text="Area", style="Toolbar.TLabel").grid(row=0, column=6, padx=(0, 4), pady=2, sticky="w")
        self.area_var = tk.StringVar(value="All")
        self.area_box = ttk.Combobox(top, textvariable=self.area_var, state="readonly",
                                      values=["All"], width=12)
        self.area_box.current(0)
        self.area_box.grid(row=0, column=7, padx=(0, 14), pady=2)
        self.area_box.bind("<<ComboboxSelected>>", self._on_area_dropdown_change)

        self.load_btn = ttk.Button(top, text="Load lineups", style="Accent.TButton", command=self._start_load)
        self.load_btn.grid(row=0, column=8, padx=(0, 6), pady=2)

        self.refresh_btn = ttk.Button(top, text="\u21bb", width=3, command=self._start_refresh)
        self.refresh_btn.grid(row=0, column=9, padx=(0, 14), pady=2)

        self.topmost_var = tk.BooleanVar(value=False)
        # Plain tk.Checkbutton, not ttk — on native Windows themes, ttk's
        # checkbox indicator ignores style overrides entirely and falls
        # back to the raw OS checkbox (a stark white box), which is
        # exactly the clash being fixed here. Classic Tk widgets honor
        # explicit colors reliably across platforms.
        topmost_chk = tk.Checkbutton(top, text="Always on top", variable=self.topmost_var,
                                      command=self._toggle_topmost,
                                      bg=TOOLBAR, fg=TEXT, selectcolor=MUTED,
                                      activebackground=TOOLBAR, activeforeground=TEXT,
                                      highlightthickness=0, borderwidth=0,
                                      font=("Segoe UI", 10), cursor="hand2")
        topmost_chk.grid(row=0, column=10, padx=(0, 14), pady=2)

        self.lock_size_var = tk.BooleanVar(value=True)
        lock_size_chk = tk.Checkbutton(top, text="Lock window size", variable=self.lock_size_var,
                                        command=self._toggle_lock_size,
                                        bg=TOOLBAR, fg=TEXT, selectcolor=MUTED,
                                        activebackground=TOOLBAR, activeforeground=TEXT,
                                        highlightthickness=0, borderwidth=0,
                                        font=("Segoe UI", 10), cursor="hand2")
        lock_size_chk.grid(row=0, column=11, padx=0, pady=2)

        self.status_var = tk.StringVar(value="Pick a map + nade type, then Load.")
        ttk.Label(top, textvariable=self.status_var, style="Toolbar.TLabel").grid(
            row=1, column=0, columnspan=10, sticky="w", pady=(8, 0))

        divider = tk.Frame(self, height=1, bg="#232a2b")
        divider.pack(side="top", fill="x")

        body = ttk.Frame(self, padding=(14, 12, 14, 14))
        body.pack(side="top", fill="both", expand=True)

        left = ttk.Frame(body, width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="Map (click a zone to filter)", foreground="#6b7677").pack(
            side="top", anchor="w", pady=(0, 4))

        self.nuke_level_row = ttk.Frame(left)
        self.nuke_outside_btn = ttk.Button(self.nuke_level_row, text="Outside / Upper",
                                            command=lambda: self._set_nuke_level("outside"))
        self.nuke_inside_btn = ttk.Button(self.nuke_level_row, text="Inside / B Site",
                                           command=lambda: self._set_nuke_level("inside"))
        self.nuke_outside_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.nuke_inside_btn.pack(side="left", expand=True, fill="x", padx=(3, 0))
        # packed/unpacked dynamically — only shown when Nuke is loaded

        self.map_canvas = tk.Canvas(left, width=292, height=258, bg="#171b1c",
                                     highlightthickness=0, borderwidth=0)
        self.map_canvas.pack(side="top", fill="both", expand=True, pady=(0, 4))
        self._zone_boxes = []  # list of (area, x1, y1, x2, y2) in canvas px, for click hit-testing
        self._map_bg_photo = None  # keep a reference so tkinter doesn't GC it
        self._last_areas = []  # remembered so a window resize can redraw without recomputing
        self._resize_after_id = None
        self.map_canvas.bind("<Button-1>", self._on_zone_click)
        self.map_canvas.bind("<Configure>", self._on_canvas_resize)
        self.map_canvas.create_text(146, 129, text="Load a map to see its zones",
                                     fill="#5d6768", font=("Segoe UI", 9), width=260)

        legend = ttk.Frame(left)
        legend.pack(side="top", anchor="w", pady=(0, 6))
        tk.Label(legend, text="\u25cf", fg="#e0602f", bg="#12161a", font=("Segoe UI", 9)).pack(side="left")
        ttk.Label(legend, text="Land  ", foreground="#6b7677", font=("Segoe UI", 9)).pack(side="left")
        tk.Label(legend, text="\u25cb", fg="#4fc3f7", bg="#12161a", font=("Segoe UI", 9)).pack(side="left")
        ttk.Label(legend, text="Stand", foreground="#6b7677", font=("Segoe UI", 9)).pack(side="left")

        search_row = ttk.Frame(left)
        search_row.pack(side="top", fill="x", pady=(0, 2))
        ttk.Label(search_row, text="Search", foreground="#6b7677").pack(side="left")
        self.favorites_only_var = tk.BooleanVar(value=False)
        favorites_chk = tk.Checkbutton(search_row, text="\u2605 Favorites only", variable=self.favorites_only_var,
                                        command=self._refresh_list,
                                        bg="#12161a", fg="#e8a23a", selectcolor="#6b7677",
                                        activebackground="#12161a", activeforeground="#e8a23a",
                                        highlightthickness=0, borderwidth=0,
                                        font=("Segoe UI", 9), cursor="hand2")
        favorites_chk.pack(side="right")
        self.search_var = tk.StringVar(value="")
        search_entry = tk.Entry(left, textvariable=self.search_var, bg="#171b1c", fg="#e8ecec",
                                 insertbackground="#e8ecec", relief="flat", font=("Segoe UI", 11))
        search_entry.pack(side="top", fill="x", ipady=6, pady=(0, 8))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry.bind("<Return>", self._jump_to_first_result)
        # Pressing Down from the search box jumps straight into the
        # results and selects the first one — lets you filter-then-
        # navigate without reaching for the mouse.
        search_entry.bind("<Down>", self._focus_listbox_from_search)

        list_row = ttk.Frame(left)
        list_row.pack(side="top", fill="both", expand=True)
        self.listbox = tk.Listbox(list_row, bg="#171b1c", fg="#e8ecec",
                                   selectbackground="#2a3132", selectforeground="#ffffff",
                                   activestyle="none", highlightthickness=0, borderwidth=0,
                                   font=("Segoe UI", 11), cursor="hand2")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        # Arrow-key navigation of the list itself is a built-in Tkinter
        # Listbox behavior (Up/Down move the selection, which fires
        # <<ListboxSelect>> the same as a click) — nothing extra needed
        # for that part.
        self._hover_index = None
        self.listbox.bind("<Motion>", self._on_listbox_motion)
        self.listbox.bind("<Leave>", self._on_listbox_leave)
        # Scoped to the listbox specifically (not bound globally) so it
        # doesn't fight with normal text-copy in the steps/usage boxes or
        # search field — copies the currently-selected lineup's practice
        # command straight from the list, no need to click down to the
        # Copy button separately.
        self.listbox.bind("<Control-c>", lambda _e: self._copy_cmd())
        sb = ttk.Scrollbar(list_row, command=self.listbox.yview)
        sb.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        right = ttk.Frame(body, padding=(20, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)

        # Packed FIRST with side="bottom" so it claims its space at the
        # bottom of the panel before anything else is laid out — this is
        # the actual fix for the practice command becoming unreachable:
        # no matter how long a lineup's usage text runs, or how tight the
        # window is, this row is guaranteed to stay visible. Any overflow
        # now happens in the middle (steps/usage text), never here.
        cmd_row = ttk.Frame(right)
        cmd_row.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Label(cmd_row, text="Practice-server command", foreground="#6b7677").pack(side="top", anchor="w")
        cmd_inner = ttk.Frame(cmd_row)
        cmd_inner.pack(side="top", fill="x", pady=(4, 0))
        self.cmd_var = tk.StringVar(value="")
        cmd_entry = ttk.Entry(cmd_inner, textvariable=self.cmd_var, state="readonly", font=("Consolas", 9))
        cmd_entry.pack(side="left", fill="x", expand=True, ipady=3)
        ttk.Button(cmd_inner, text="Copy", command=self._copy_cmd).pack(side="left", padx=(8, 0))

        self.img_frame = tk.Frame(right, bg="#0c0f11", height=300)
        self.img_frame.pack(side="top", fill="x")
        self.img_frame.pack_propagate(False)
        self.img_label = tk.Label(self.img_frame, bg="#0c0f11", fg="#3a4344",
                                   text="Select a lineup to see the throw",
                                   font=("Segoe UI", 11))
        self.img_label.place(relx=0.5, rely=0.5, anchor="center")

        name_row = ttk.Frame(right)
        name_row.pack(side="top", fill="x", pady=(14, 8))
        self.name_label = ttk.Label(name_row, text="Pick a lineup from the list", style="Header.TLabel")
        self.name_label.pack(side="left", anchor="w")
        self.favorite_btn = tk.Label(name_row, text="\u2606", bg="#12161a", fg="#6b7677",
                                      font=("Segoe UI", 16), cursor="hand2")
        self.favorite_btn.pack(side="left", padx=(10, 0))
        self.favorite_btn.bind("<Button-1>", lambda _e: self._toggle_favorite())

        self.badge_row = ttk.Frame(right)
        self.badge_row.pack(side="top", anchor="w")

        self.steps_text = tk.Text(right, height=3, wrap="word", bg="#171b1c", fg="#e8ecec",
                                   borderwidth=0, highlightthickness=0, padx=10, pady=6,
                                   font=("Segoe UI", 10))
        self.steps_text.pack(side="top", fill="x", pady=(14, 0))
        self.steps_text.configure(state="disabled")

        self.usage_text = tk.Text(right, height=3, wrap="word", bg="#171b1c", fg="#8f9a9b",
                                   borderwidth=0, highlightthickness=0, padx=10, pady=6,
                                   font=("Segoe UI", 10))
        self.usage_text.pack(side="top", fill="x", expand=True, pady=(10, 10))
        self.usage_text.configure(state="disabled")

    def _toggle_topmost(self):
        # Window-manager level "stay above other windows" flag — same thing
        # Discord, calculators, and note-taking apps use for a floating
        # window. Doesn't touch CS2's process in any way.
        self.attributes("-topmost", self.topmost_var.get())

    def _toggle_lock_size(self):
        # Locked = fixed size, matching the carefully-tuned default layout
        # (drag-resize disabled, maximize button greyed out). Unlocked lets
        # the window — and the zone map canvas inside it — grow or shrink;
        # _on_canvas_resize redraws the map to fit whenever that happens.
        locked = self.lock_size_var.get()
        self.resizable(not locked, not locked)

    # -- loading -----------------------------------------------------
    def _start_load(self, force_refresh=False):
        self.load_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.listbox.delete(0, "end")
        self.search_var.set("")
        self.area_var.set("All")
        self.area_box.config(values=["All"])
        self._highlight_area = None
        self._name_pins = []
        self._items = []
        self._current_item = None  # switching maps invalidates whatever was shown before
        self._update_favorite_button()
        self.name_label.config(text="Pick a lineup from the list")
        map_key = MAP_KEY_BY_LABEL[self.map_var.get()]
        nade_key = NADE_TYPES[self.nade_var.get()]
        self._current_map_key = map_key
        if force_refresh:
            # Delete this map/nade combo's cache file so load_lineups
            # can't just hand back the old cached result — without this,
            # a corrected lineup on cs2util's end would never show up
            # here no matter how many times you reload.
            try:
                os.remove(_cache_path(map_key, nade_key))
            except OSError:
                pass
        threading.Thread(target=self._load_worker, args=(map_key, nade_key), daemon=True).start()

    def _start_refresh(self):
        self._start_load(force_refresh=True)

    def _load_worker(self, map_key, nade_key):
        def progress(done, total):
            # Runs on the background thread — never touch Tk state directly
            # from here, hand it to the main loop via after().
            self.after(0, lambda: self.status_var.set(f"Fetching lineup details… {done}/{total}"))

        try:
            self.after(0, lambda: self.status_var.set("Fetching lineup list…"))
            items, failed_count = load_lineups(map_key, nade_key, progress_cb=progress)
        except Exception as e:
            self.after(0, lambda: self._load_failed(e))
            return
        self.after(0, lambda: self._load_done(items, failed_count))

    def _load_failed(self, err):
        self.load_btn.config(state="normal")
        self.refresh_btn.config(state="normal")
        self.status_var.set("Load failed.")
        messagebox.showerror(
            "Couldn't load lineups",
            f"{err}\n\nEither cs2util.com is unreachable, or its page layout "
            "changed and the parser needs an update."
        )

    def _load_done(self, items, failed_count=0):
        self._items = items
        self.load_btn.config(state="normal")
        self.refresh_btn.config(state="normal")
        status = f"{len(items)} lineups loaded."
        if failed_count:
            # Some detail pages threw an exception while fetching/parsing —
            # those items are silently missing otherwise, so say so instead
            # of just showing a slightly-smaller-than-expected list.
            status += f" ({failed_count} failed to load and were skipped.)"
        self.status_var.set(status)
        areas = sorted({item.get("area", "Other") for item in items})
        self.area_box.config(values=["All"] + areas)

        if self._current_map_key == "nuke":
            self.nuke_level_row.pack(side="top", fill="x", pady=(0, 6))
        else:
            self.nuke_level_row.pack_forget()
        self._update_nuke_level_buttons()

        self._draw_zone_map(areas)
        self._refresh_list()

    def _set_nuke_level(self, level):
        self._nuke_level = level
        self._update_nuke_level_buttons()
        areas = sorted({it.get("area", "Other") for it in self._items})
        self._draw_zone_map(areas)

    def _update_nuke_level_buttons(self):
        outside_style = "Accent.TButton" if self._nuke_level == "outside" else "TButton"
        inside_style = "Accent.TButton" if self._nuke_level == "inside" else "TButton"
        self.nuke_outside_btn.configure(style=outside_style)
        self.nuke_inside_btn.configure(style=inside_style)

    def _on_canvas_resize(self, _event):
        # Fires continuously while dragging the window edge — redrawing the
        # full zone map (image resize + every box) on each of those would
        # be janky, so wait for a short pause in resizing before redrawing.
        if self._current_map_key is None:
            return  # nothing loaded yet — the static placeholder text is fine as-is
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(120, lambda: self._draw_zone_map(self._last_areas))

    def _draw_zone_map(self, areas):
        """Draw the clickable zone map for the currently loaded map. If a
        real image has been placed in map_images/ for this map, it's used
        as the background with calibrated hotspot regions overlaid;
        otherwise falls back to the plain schematic. Areas with a known
        position are placed geographically; anything else lands in an
        auto-generated grid strip so it's still clickable."""
        c = self.map_canvas
        c.delete("all")
        self._zone_boxes = []
        self._last_areas = areas
        # Use the canvas's real current size (it can grow/shrink once the
        # window is unlocked) rather than the old fixed 292x258 — guarded
        # with a fallback in case this fires before the widget is mapped.
        W, H = c.winfo_width(), c.winfo_height()
        if W <= 1 or H <= 1:
            W, H = 292, 258
        map_key = self._current_map_key
        # Nuke has two real levels sharing one coordinate space — look up
        # image/regions under "nuke_outside"/"nuke_inside" instead of "nuke".
        lookup_key = f"nuke_{self._nuke_level}" if map_key == "nuke" else map_key
        norm_hints = {k.lower(): v for k, v in MAP_ZONE_LAYOUT.get(map_key, {}).items()}
        norm_regions = {k.lower(): v for k, v in MAP_IMAGE_REGIONS.get(lookup_key, {}).items()}

        img_path = _find_map_image(lookup_key)
        img_box = None  # (ox, oy, draw_w, draw_h) — where the image was placed on canvas
        if img_path:
            try:
                img = Image.open(img_path).convert("RGB")
                scale = min(W / img.width, H / img.height)
                draw_w, draw_h = int(img.width * scale), int(img.height * scale)
                img = img.resize((draw_w, draw_h))
                ox, oy = (W - draw_w) // 2, (H - draw_h) // 2
                self._map_bg_photo = ImageTk.PhotoImage(img)
                c.create_image(ox, oy, anchor="nw", image=self._map_bg_photo)
                img_box = (ox, oy, draw_w, draw_h)
            except Exception:
                img_path = None  # fall through to schematic if the file's unreadable

        use_regions = img_box is not None and norm_regions
        hints = norm_regions if use_regions else norm_hints
        hinted = [a for a in areas if a.lower() in hints]
        unhinted = [a for a in areas if a.lower() not in hints]

        def add_box(area, x1, y1, x2, y2, label_at="center", show_label=True, rel_area=None):
            selected = (self._highlight_area == area)
            # Visual hierarchy: a big "container" region (like A Site) and a
            # small precise one nested inside it (like A Ramp) used to look
            # equally prominent, which reads as confusing overlap rather
            # than "one specific highlighted spot". Big boxes now default to
            # a thin, muted outline so they recede into the background;
            # small ones stay bright since they're the more likely target.
            # Selection always wins, regardless of size.
            is_large = rel_area is not None and rel_area > 0.05
            if selected:
                outline = "#e8a23a"
                width = 2
            elif use_regions:
                outline = "#3a4a56" if is_large else "#5aa9e6"
                width = 1
            else:
                outline = "#3a4344"
                width = 1
            fill = "#e8a23a" if (selected and not use_regions) else ""
            c.create_rectangle(x1, y1, x2, y2, outline=outline, fill=fill, width=width)
            self._zone_boxes.append((area, x1, y1, x2, y2))
            if not show_label:
                return

            # Always label the box — unhinted grid-strip boxes have no
            # baked-in text at all, and even the calibrated A/B Site boxes
            # on a real image don't necessarily have one clean label to
            # reference, so a small pill with a dark backing keeps it
            # legible over a busy image either way.
            text_fill = "#12161a" if selected else ("#8a97a0" if is_large else "#e8ecec")
            bg_fill = "#e8a23a" if selected else "#12161a"
            cx = (x1 + x2) / 2
            cy = y1 + 9 if label_at == "top" else (y1 + y2) / 2
            tid = c.create_text(cx, cy, text=area, fill=text_fill,
                                 font=("Segoe UI Semibold", 7), width=max(x2 - x1 - 6, 38))
            bbox = c.bbox(tid)
            if bbox:
                pad = 2
                bg = c.create_rectangle(bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
                                         fill=bg_fill, outline="")
                c.tag_lower(bg, tid)

        if use_regions:
            ox, oy, draw_w, draw_h = img_box
            img_area = draw_w * draw_h
            # Collect every box first so they can be drawn largest-first —
            # otherwise a big box drawn after a small one visually buries
            # the small one's outline right where they overlap.
            pending = []
            for area in hinted:
                region = norm_regions[area.lower()]
                # An area can map to either one box, or a list of boxes
                # (e.g. "Middle" covering two separate dot clusters) —
                # only the first box gets the text label, so the name
                # isn't repeated on every piece.
                boxes = region if isinstance(region, list) else [region]
                for i, (rx1, ry1, rx2, ry2) in enumerate(boxes):
                    x1, y1 = ox + rx1 * draw_w, oy + ry1 * draw_h
                    x2, y2 = ox + rx2 * draw_w, oy + ry2 * draw_h
                    rel_area = ((x2 - x1) * (y2 - y1)) / img_area if img_area else 0
                    pending.append((rel_area, area, x1, y1, x2, y2, i == 0))
            pending.sort(key=lambda p: p[0], reverse=True)  # largest first — drawn underneath
            for rel_area, area, x1, y1, x2, y2, show_label in pending:
                add_box(area, x1, y1, x2, y2, label_at="top", show_label=show_label, rel_area=rel_area)
        else:
            for area in hinted:
                rx, ry = norm_hints[area.lower()]
                cx, cy = rx * W, ry * H
                add_box(area, cx - 38, cy - 14, cx + 38, cy + 14)

        if unhinted:
            step = W / len(unhinted)
            for i, area in enumerate(unhinted):
                cx = step * i + step / 2
                add_box(area, cx - min(step - 6, 90) / 2, H - 30,
                        cx + min(step - 6, 90) / 2, H - 8)

        if not hints and not img_path:
            c.create_text(W / 2, 12, text="(no researched layout for this map yet — plain grid)",
                           fill="#5d6768", font=("Segoe UI", 8))

        # Pin the exact spot(s) guessed from the selected lineup's own
        # name — only meaningful on a real image, where a precise point
        # actually corresponds to something visible. "land" (the smoke's
        # target) and "stand" (the throw origin) are visually distinct —
        # a solid dot for land, a ring for stand — since they're two
        # different concepts and both can be pinned for the same lineup.
        if use_regions and self._name_pins:
            ox, oy, draw_w, draw_h = img_box
            for label, rx, ry, kind in self._name_pins:
                px, py = ox + rx * draw_w, oy + ry * draw_h
                if kind == "stand":
                    c.create_oval(px - 4, py - 4, px + 4, py + 4,
                                   outline="#4fc3f7", width=2)
                    c.create_oval(px - 1, py - 1, px + 1, py + 1, fill="#4fc3f7", outline="")
                else:
                    c.create_oval(px - 3.5, py - 3.5, px + 3.5, py + 3.5,
                                   fill="#e0602f", outline="#ffffff", width=1)

        # Smaller/more specific regions (e.g. "Window" or "Connector")
        # often sit fully inside a bigger one (e.g. "Mid" or "A Site").
        # Hit-testing checks this list in order and stops at the first
        # match, so sort smallest-area-first — otherwise a click inside a
        # nested small box would always resolve to the larger box around it.
        self._zone_boxes.sort(key=lambda b: (b[3] - b[1]) * (b[4] - b[2]))

    def _on_zone_click(self, event):
        for area, x1, y1, x2, y2 in self._zone_boxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if self.area_var.get() == area:
                    # clicking an already-selected zone deselects it
                    self.area_var.set("All")
                    self._highlight_area = None
                else:
                    self.area_var.set(area)
                    self._highlight_area = area
                self._refresh_list()
                # If this area only lives on Nuke's other level (e.g. B Site
                # was clicked from the fallback grid while showing Outside),
                # switch levels so it renders properly positioned.
                if self._current_map_key == "nuke" and self._highlight_area:
                    other_level = "inside" if self._nuke_level == "outside" else "outside"
                    current_regions = MAP_IMAGE_REGIONS.get(f"nuke_{self._nuke_level}", {})
                    other_regions = MAP_IMAGE_REGIONS.get(f"nuke_{other_level}", {})
                    if area.lower() not in {k.lower() for k in current_regions} and \
                       area.lower() in {k.lower() for k in other_regions}:
                        self._nuke_level = other_level
                        self._update_nuke_level_buttons()
                areas = sorted({it.get("area", "Other") for it in self._items})
                self._draw_zone_map(areas)
                return

    def _on_area_dropdown_change(self, _evt):
        self._highlight_area = self.area_var.get() if self.area_var.get() != "All" else None
        self._refresh_list()
        areas = sorted({it.get("area", "Other") for it in self._items})
        self._draw_zone_map(areas)

    def _refresh_list(self):
        side = self.side_var.get()
        area = self.area_var.get()
        query = self.search_var.get().strip().lower()
        favorites_only = self.favorites_only_var.get()
        self.listbox.delete(0, "end")
        self._hover_index = None
        pool = []
        for item in self._items:
            if side != "All" and item.get("team") and item["team"] != side:
                continue
            if area != "All" and item.get("area", "Other") != area:
                continue
            if query and query not in item["name"].lower():
                continue
            if favorites_only and item.get("url") not in self._favorites:
                continue
            pool.append(item)
        pool.sort(key=lambda item: item["name"].lower())
        self._visible = pool
        for item in pool:
            team = item.get("team")
            tag = f"{team}  " if team else "?   "
            star = "\u2605 " if item.get("url") in self._favorites else ""
            self.listbox.insert("end", f"{tag}{star}{item['name']}")
            idx = self.listbox.size() - 1
            self.listbox.itemconfig(idx, fg=TEAM_COLOR.get(team, "#8f9a9b"))

    def _on_listbox_motion(self, event):
        idx = self.listbox.nearest(event.y)
        if idx == self._hover_index:
            return
        selected = set(self.listbox.curselection())
        if self._hover_index is not None and self._hover_index not in selected:
            self.listbox.itemconfig(self._hover_index, background="#171b1c")
        if idx not in selected:
            self.listbox.itemconfig(idx, background="#1e2426")
        self._hover_index = idx

    def _on_listbox_leave(self, _evt):
        if self._hover_index is not None and self._hover_index not in set(self.listbox.curselection()):
            self.listbox.itemconfig(self._hover_index, background="#171b1c")
        self._hover_index = None

    # -- selection -----------------------------------------------------
    def _toggle_favorite(self):
        item = self._current_item
        if not item or not item.get("url"):
            return
        url = item["url"]
        if url in self._favorites:
            self._favorites.discard(url)
        else:
            self._favorites.add(url)
        save_favorites(self._favorites)
        self._update_favorite_button()
        self._refresh_list()  # updates the star prefix on the list row

    def _update_favorite_button(self):
        item = self._current_item
        is_favorite = bool(item) and item.get("url") in self._favorites
        if is_favorite:
            self.favorite_btn.config(text="\u2605", fg="#e8a23a")
        else:
            self.favorite_btn.config(text="\u2606", fg="#6b7677")

    def _jump_to_first_result(self, _evt=None):
        if not getattr(self, "_visible", None):
            return
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        self.listbox.see(0)
        self._on_select(None)

    def _focus_listbox_from_search(self, _evt=None):
        """Down arrow in the search box: move focus into the list and
        select the first result, so filtering-then-browsing doesn't need
        the mouse. Returns 'break' so the Entry widget doesn't also try
        to move its own cursor."""
        if not getattr(self, "_visible", None):
            return "break"
        self.listbox.focus_set()
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(0)
        self.listbox.activate(0)
        self.listbox.see(0)
        self._on_select(None)
        return "break"

    def _on_select(self, _evt):
        sel = self.listbox.curselection()
        if not sel:
            return
        item = self._visible[sel[0]]
        self.name_label.config(text=item["name"])
        self._current_item = item
        self._update_favorite_button()

        # Highlight this lineup's zone on the map, independent of whatever
        # the Area filter is currently set to — so browsing the full list
        # still shows you where each one is. Also try to pin the exact
        # spot(s): the "land" target always comes from the lineup's name;
        # "stand" prefers the real setpos coordinates (converted via
        # MAP_CALIBRATION) when available, since that's actual game data
        # rather than a name-matching guess, falling back to the name
        # match if this map isn't calibrated or setpos didn't parse.
        item_area = item.get("area")
        new_pins = _guess_callout_pins(self._current_map_key, item.get("name", ""))
        exact_stand = _setpos_stand_point(self._current_map_key, item.get("console") or "")
        if exact_stand is not None:
            new_pins = [p for p in new_pins if p[3] != "stand"]
            new_pins.append(("stand (exact)", exact_stand[0], exact_stand[1], "stand"))
        area_changed = bool(item_area) and item_area != self._highlight_area
        if area_changed or new_pins != self._name_pins:
            if area_changed:
                self._highlight_area = item_area
            self._name_pins = new_pins
            if self._current_map_key == "nuke" and area_changed:
                other_level = "inside" if self._nuke_level == "outside" else "outside"
                current_regions = MAP_IMAGE_REGIONS.get(f"nuke_{self._nuke_level}", {})
                other_regions = MAP_IMAGE_REGIONS.get(f"nuke_{other_level}", {})
                if item_area.lower() not in {k.lower() for k in current_regions} and \
                   item_area.lower() in {k.lower() for k in other_regions}:
                    self._nuke_level = other_level
                    self._update_nuke_level_buttons()
            areas = sorted({it.get("area", "Other") for it in self._items})
            self._draw_zone_map(areas)

        # A new lineup was picked — any video from the previous one needs
        # to stop before its badge_row chip gets destroyed below, or the
        # frame-timer would keep firing against a dead widget.
        self._stop_video_playback()

        for w in self.badge_row.winfo_children():
            w.destroy()
        self.video_chip = None  # the widget just got destroyed above; only reassigned below if this item has a video
        badges = []
        if item.get("team"):
            badges.append((f"{item['team']} SIDE", TEAM_COLOR.get(item["team"], "#8f9a9b")))
        if item.get("difficulty"):
            badges.append((item["difficulty"], DIFF_COLOR.get(item["difficulty"], "#8f9a9b")))
        for color, text in (
            ("#8f9a9b", item.get("mouse")),
            ("#8f9a9b", "Jump-throw" if (item.get("jump_throw") or "").lower() == "yes" else None),
            ("#8f9a9b", f"Air time {item['air_time']}s" if item.get("air_time") else None),
        ):
            if text:
                badges.append((text, color))
        for text, color in badges:
            chip = tk.Label(self.badge_row, text=text, bg="#1b2021", fg=color,
                             font=("Segoe UI Semibold", 9), padx=9, pady=3)
            chip.pack(side="left", padx=(0, 6), pady=(0, 4))

        if item.get("video"):
            video_url = item["video"]
            if VIDEO_PLAYBACK_AVAILABLE:
                chip_text = "\u23f9 Stop video" if (self._video_playing and self._video_url == video_url) else "\u25b6 Watch video"
                self.video_chip = tk.Label(self.badge_row, text=chip_text, bg="#1b2021", fg="#5aa9e6",
                                            font=("Segoe UI Semibold", 9), padx=9, pady=3, cursor="hand2")
                self.video_chip.pack(side="left", padx=(0, 6), pady=(0, 4))
                self.video_chip.bind("<Button-1>", lambda _e, u=video_url: self._toggle_video_playback(u))
            else:
                # imageio isn't installed — fall back to opening the clip
                # in a browser tab instead of playing it inline.
                video_chip = tk.Label(self.badge_row, text="\u25b6 Watch video (browser)", bg="#1b2021", fg="#5aa9e6",
                                       font=("Segoe UI Semibold", 9), padx=9, pady=3, cursor="hand2")
                video_chip.pack(side="left", padx=(0, 6), pady=(0, 4))
                video_chip.bind("<Button-1>", lambda _e, u=video_url: webbrowser.open(u))

        self._set_text(self.steps_text, item.get("steps") or "No step-by-step text found for this one — check the image and the source link.")
        self._set_text(self.usage_text, item.get("usage") or "")
        self.cmd_var.set(item.get("console") or "")

        self._image_request_id += 1
        request_id = self._image_request_id
        if item.get("image"):
            self.img_label.config(image="", text="Loading image…", fg="#5d6768")
            threading.Thread(target=self._load_image, args=(item["image"], request_id), daemon=True).start()
        else:
            self.img_label.config(image="", text="No image found for this lineup", fg="#5d6768")

    def _load_image(self, url, request_id):
        try:
            img = get_image(url)
        except Exception:
            # Only show the failure if this is still the current selection —
            # an old, since-abandoned request failing shouldn't overwrite
            # whatever the user has since clicked on.
            def show_failure():
                if request_id == self._image_request_id:
                    self.img_label.config(image="", text="Image failed to load", fg="#8f9a9b")
            self.after(0, show_failure)
            return
        # fill most of the image frame while preserving aspect ratio
        frame_w = max(self.img_frame.winfo_width(), 640)
        frame_h = max(self.img_frame.winfo_height(), 360)
        img.thumbnail((frame_w - 20, frame_h - 20))
        # PhotoImage creation is a Tk/Tcl call — must happen on the main
        # thread, so pass the plain PIL image over and build it in apply().
        # Two lineups can be loading at once if you click quickly on a slow
        # connection; without this check, whichever request happens to
        # finish LAST wins, which may not be the currently-selected one.
        # request_id lets a stale result recognize it's outdated and no-op.
        def apply():
            if request_id != self._image_request_id:
                return
            photo = ImageTk.PhotoImage(img)
            self._photo = photo
            self.img_label.config(image=photo, text="")
        self.after(0, apply)

    # -- in-app video playback ------------------------------------------
    # Silent frame-by-frame playback (imageio has no audio decoding) —
    # decodes the whole short clip to a list of frames up front rather
    # than streaming, since these are only a few seconds long, then just
    # walks the list on a self.after() timer, looping back to frame 0.

    def _toggle_video_playback(self, video_url):
        if self._video_playing and self._video_url == video_url:
            self._stop_video_playback()
            return
        self._stop_video_playback()  # stop whatever else might be playing first
        self._start_video_playback(video_url)

    def _start_video_playback(self, video_url):
        self._video_playing = True
        self._video_url = video_url
        self._video_playback_id += 1
        request_id = self._video_playback_id
        if self.video_chip is not None:
            self.video_chip.config(text="Loading video\u2026")
        self.img_label.config(image="", text="Loading video\u2026", fg="#5d6768")
        threading.Thread(target=self._load_video_worker, args=(video_url, request_id), daemon=True).start()

    def _load_video_worker(self, video_url, request_id):
        try:
            path = get_video_path(video_url)
            # Cheap first open just to read source size/fps — this alone
            # doesn't decode any frames, so it's fast regardless of clip
            # length (confirmed: ~0.1s even on a several-second clip).
            probe = imageio.get_reader(path)
            meta = probe.get_meta_data()
            src_w, src_h = meta.get("size", (640, 360))
            src_fps = meta.get("fps") or 30
            probe.close()

            frame_w = max(self.img_frame.winfo_width(), 640) - 20
            frame_h = max(self.img_frame.winfo_height(), 360) - 20
            # Scale to fit the display area, preserving the source aspect
            # ratio (requesting a mismatched ratio from ffmpeg would
            # stretch/distort the picture) — even dimensions since some
            # codecs' scale filters require it.
            scale = min(frame_w / src_w, frame_h / src_h, 1.0)
            target_w = max(2, int(src_w * scale) // 2 * 2)
            target_h = max(2, int(src_h * scale) // 2 * 2)
            # Cap playback fps too — a loop preview doesn't need the
            # source's full 30/60fps, and decoding fewer frames is most
            # of the actual speed win. 24fps matches standard film/movie
            # cadence rather than an arbitrary round number.
            target_fps = min(src_fps, 24)

            # The real fix: asking ffmpeg to scale and drop frames itself
            # during decode (native code) instead of decoding every full-
            # resolution source frame in Python and resizing afterward —
            # measured ~10x faster on a representative test clip (3.9s ->
            # 0.4s), which is what was making "Watch video" slow to start.
            reader = imageio.get_reader(path, size=f"{target_w}x{target_h}", fps=target_fps)
            frames = [Image.fromarray(frame) for frame in reader]
            reader.close()
        except Exception:
            self.after(0, lambda: self._video_load_failed(request_id))
            return
        self.after(0, lambda: self._video_frames_ready(frames, target_fps, request_id))

    def _video_load_failed(self, request_id):
        if request_id != self._video_playback_id:
            return  # stopped or superseded while loading — don't clobber whatever's shown now
        self._video_playing = False
        if self.video_chip is not None:
            self.video_chip.config(text="\u25b6 Watch video")
        self.img_label.config(image="", text="Video failed to load", fg="#8f9a9b")

    def _video_frames_ready(self, frames, fps, request_id):
        if request_id != self._video_playback_id or not self._video_playing:
            return  # stopped while it was loading
        self._video_fps = fps
        self._video_photo_frames = [ImageTk.PhotoImage(f) for f in frames]
        if self.video_chip is not None:
            self.video_chip.config(text="\u23f9 Stop video")
        self._play_video_frame(0, request_id)

    def _play_video_frame(self, index, request_id):
        if request_id != self._video_playback_id or not self._video_playing:
            return
        frames = self._video_photo_frames
        if not frames:
            return
        photo = frames[index % len(frames)]
        self._photo = photo  # keep a reference so Tk doesn't garbage-collect it mid-display
        self.img_label.config(image=photo, text="")
        delay_ms = max(int(1000 / self._video_fps), 20)
        self._video_after_id = self.after(delay_ms, lambda: self._play_video_frame(index + 1, request_id))

    def _stop_video_playback(self):
        was_playing = self._video_playing
        self._video_playing = False
        self._video_playback_id += 1  # invalidates any in-flight load or scheduled frame
        if self._video_after_id is not None:
            self.after_cancel(self._video_after_id)
            self._video_after_id = None
        self._video_photo_frames = None
        if self.video_chip is not None:
            self.video_chip.config(text="\u25b6 Watch video")
        if not was_playing:
            return
        # restore the static cover image for whatever's currently selected
        item = self._current_item
        if item and item.get("image"):
            self._image_request_id += 1
            request_id = self._image_request_id
            self.img_label.config(image="", text="Loading image\u2026", fg="#5d6768")
            threading.Thread(target=self._load_image, args=(item["image"], request_id), daemon=True).start()

    def _set_text(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _copy_cmd(self):
        cmd = self.cmd_var.get()
        if not cmd:
            return
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.status_var.set("Command copied.")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        # Checks the calibration data (zone boxes, callout points, setpos
        # fits) for the kinds of mistakes found and fixed during this
        # project's development — run this after editing any map data.
        from calibration_data import run_selftest
        ok, _ = run_selftest()
        sys.exit(0 if ok else 1)
    app = LineupApp()
    app.mainloop()