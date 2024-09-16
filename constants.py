#!/usr/bin/env python3

# * This file contains constants used in the application
# * Change the following paths according to your setup

import os

MONGO_URI = "mongodb://192.168.1.206:27097/launcher?authSource=admin"

# Playnite constants
PLAYNITE_IMAGE_DIR = "D:\\Playnite\\library\\files"
# * Place the Playnite URL shortcuts in the following directory
PLAYNITE_SHORTCUTS_DIR = (
    "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Games"
)

# Derived constants
CURR_PATH = os.path.dirname(os.path.abspath(__file__))
FALLBACK_POSTER = os.path.join(CURR_PATH, "assets", "placeholder.jpg")
