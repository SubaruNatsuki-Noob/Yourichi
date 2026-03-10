"""
Smart anime/movie filename parser + caption template renderer.

Supported variables:
  {title}       — full title (separators → spaces)
  {clean_title} — show/anime name only (tags stripped)
  {episode}     — episode number  e.g. 01
  {season}      — season number   e.g. 04
  {quality}     — 1080p / 720p / 4K etc.
  {extension}   — mkv / mp4 etc.
"""
import re

_RE_SEASON  = re.compile(r"[Ss](\d{1,2})")
_RE_EPISODE = re.compile(
    r"[Ee](\d{1,3})"
    r"|[Ee][Pp](\d{1,3})"
    r"|[Ee]pisode[\s._-]?(\d{1,3})"
)
_RE_QUALITY = re.compile(
    r"(2160[Pp]|1080[Pp]|720[Pp]|480[Pp]|360[Pp]|4[Kk]|FHD|HD|SD)",
    re.IGNORECASE,
)
_RE_GARBAGE = re.compile(
    r"[\[\(].*?[\]\)]"
    r"|[Ss]\d{1,2}[Ee]\d{1,3}"
    r"|[Ee][Pp]?\d{1,3}"
    r"|2160[Pp]|1080[Pp]|720[Pp]|480[Pp]|360[Pp]|4[Kk]|FHD|HD|SD"
    r"|BluRay|BDRip|WEB-?DL|WEBRip|HDTV|DVDRip|DVDScr|CAMRip"
    r"|x264|x265|HEVC|AVC|AAC|AC3|DTS|DD5\.1|10bit|Hi10P"
    r"|Multi|Dual|Hindi|English|Japanese|Sub|Dub|Dubbed|Subbed"
    r"|REPACK|PROPER|EXTENDED|UNRATED|DC|THEATRICAL"
    r"|\.\w{2,4}$",
    re.IGNORECASE,
)
_RE_SEP = re.compile(r"[._\-]+")


def parse_filename(filename: str) -> dict:
    name = filename.rsplit("/", 1)[-1]

    extension = ""
    if "." in name:
        base, ext = name.rsplit(".", 1)
        if len(ext) <= 4:
            extension = ext.lower()
            name = base

    spaced = re.sub(r"[._]", " ", name)

    season_m = _RE_SEASON.search(spaced)
    season   = season_m.group(1).zfill(2) if season_m else ""

    ep_m = _RE_EPISODE.search(spaced)
    if ep_m:
        episode = next(g for g in ep_m.groups() if g is not None).zfill(2)
    else:
        episode = ""

    quality_m = _RE_QUALITY.search(spaced)
    quality   = quality_m.group(1) if quality_m else ""

    title = spaced.strip()

    clean = _RE_GARBAGE.sub(" ", name)
    clean = _RE_SEP.sub(" ", clean).strip()
    clean = re.sub(
        r"\b(" + _RE_QUALITY.pattern + r")\b", "", clean, flags=re.IGNORECASE
    )
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    return {
        "title":       title,
        "clean_title": clean,
        "episode":     episode,
        "season":      season,
        "quality":     quality,
        "extension":   extension,
    }


def render_caption(template: str, filename: str, fallback: str = "") -> str:
    if not template:
        return fallback
    meta = parse_filename(filename)
    try:
        return template.format_map(meta)
    except (KeyError, ValueError):
        return template
