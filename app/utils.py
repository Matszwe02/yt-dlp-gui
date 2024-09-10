import json
from pathlib import Path

ROOT = Path(__file__).parent

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def save_json(path, data: dict):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)