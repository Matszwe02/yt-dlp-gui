import json
from pathlib import Path
import os

ROOT = Path(__file__).parent

def load_json(path):
    
    if not os.path.isfile(path):
        with open(path, 'w') as f:
            json.dump(EXAMPLE_CONFIG, f, indent=4)
    
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def save_json(path, data: dict):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)




EXAMPLE_CONFIG = {
  "format": 0,
  "onedl": True,
  "autostart": True,
  "ctrlv": True,
  "isme": False,
  "mkvremux": False,
  "clipboardmonitor": False,
  "presets": {
    "best": {
      "default": True,
      "args": [
        "-f",
        "bv*[ext=mp4]+ba/b[ext=mp4]"
      ],
      "path": "",
      "sponsorblock": "remove",
      "metadata": True,
      "subtitles": False,
      "autosubtitles": True,
      "thumbnail": True,
      "extra_args": "",
      "filename": "%(title)s %(upload_date>%Y-%m-%d)s.%(ext)s",
      "embedsubs": True,
      "markwatch": False
    },
    "1080": {
      "default": True,
      "args": [
        "-f",
        "bv*[height<=1080][ext=mp4]+ba/b"
      ],
      "path": "",
      "sponsorblock": "remove",
      "sponsorblock_categories": [
        "Sponsor",
        "Non-Music"
      ],
      "metadata": True,
      "subtitles": False,
      "autosubtitles": True,
      "thumbnail": True,
      "extra_args": "",
      "filename": "%(title)s %(upload_date>%Y-%m-%d)s.%(ext)s",
      "embedsubs": True,
      "markwatch": False
    },
    "mp4": {
      "default": True,
      "args": [
        "-f",
        "bv*[vcodec^=avc]+ba[ext=m4a]/b"
      ],
      "path": "",
      "sponsorblock": "remove",
      "sponsorblock_categories": [
        "Sponsor",
        "Non-Music"
      ],
      "metadata": True,
      "subtitles": False,
      "autosubtitles": True,
      "thumbnail": True,
      "extra_args": "",
      "filename": "%(title)s %(upload_date>%Y-%m-%d)s.%(ext)s",
      "embedsubs": True,
      "markwatch": False
    },
    "mp3": {
      "default": True,
      "args": [
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0"
      ],
      "path": "",
      "sponsorblock": "remove",
      "sponsorblock_categories": [
        "Sponsor",
        "Non-Music"
      ],
      "metadata": True,
      "subtitles": False,
      "autosubtitles": True,
      "thumbnail": True,
      "extra_args": "",
      "filename": "%(title)s %(upload_date>%Y-%m-%d)s.%(ext)s",
      "embedsubs": True,
      "markwatch": False
    }
  }
    
    }