import os
from pathlib import Path
import yaml


def load_config(path=None):
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project_root():
    return Path(__file__).resolve().parent.parent
