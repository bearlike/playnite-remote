#!/usr/bin/env python3
import os
from typing import Optional
import glob
from PIL import Image
import streamlit as st
import configparser
import constants


def parse_url_file(file_path: str) -> tuple:
    """Function to parse the .url files and extract necessary details
    Args:
        file_path (str): The path to the .url file
    Returns:
        tuple: (icon_file, url)
    """
    config = configparser.ConfigParser()
    config.read(file_path)

    # Extract IconFile and URL from the .url file
    icon_file = config.get("InternetShortcut", "IconFile", fallback=None)
    url = config.get("InternetShortcut", "URL", fallback=None)

    return icon_file, url


def find_image_for_uuid(uuid: str) -> Optional[str]:
    """Function to find suitable image from the UUID folder
    Args:
        uuid (str): The UUID to search for
    Returns:
        Optional[str]: The path to the suitable image or None
    """

    image_dir = os.path.join(constants.PLAYNITE_IMAGE_DIR, uuid)

    # Supported image formats
    extensions = ["jpg", "jpeg", "png", "webp"]

    # Get all images in the folder
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(image_dir, f"*.{ext}")))

    # Check image dimensions and select the appropriate one
    for image_path in images:
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                # Non-square (e.g. not 256x256) and landscape images above 1000px
                if height > width and width < 1000 and height < 1000:
                    return image_path
        except Exception as e:
            st.warning(f"Error reading image {image_path}: {e}")

    # No suitable image found
    return None


def execute_command(command: str, cwd: str) -> None:
    """Function to execute a command in the given directory"""
    try:
        to_run = ""
        if cwd:
            to_run += f"cd {cwd} &&"
        elif command:
            to_run += f"{command}"

        to_run = to_run.strip()
        os.system(to_run)
        st.toast(f"Executed: `{command}`", icon="✅")

    except Exception as e:
        st.toast(f"Error executing command: `{str(e)}`", icon="❌")


def display_pagination_controls(page_number, total_pages):
    """
    Display pagination controls and update the query parameters based on user input.

    Args:
        page_number (int): Current page number.
        total_pages (int): Total number of pages.
    """
    page_btn_container = st.container(border=True)
    with page_btn_container:
        prev_disabled = page_number <= 1
        next_disabled = page_number >= total_pages

        prev_col, page_col, next_col = st.columns([1, 2, 1])

        with prev_col:
            st.button(
                ":arrow_backward: Previous",
                disabled=prev_disabled,
                on_click=lambda: st.query_params.update({"page": page_number - 1}),
                use_container_width=True,
                key="prev_button",
            )

        with page_col:
            st.button(
                f"Page {page_number} of {total_pages}",
                use_container_width=True,
                disabled=True,
            )

        with next_col:
            st.button(
                "Next :arrow_forward:",
                disabled=next_disabled,
                on_click=lambda: st.query_params.update({"page": page_number + 1}),
                use_container_width=True,
                key="next_button",
            )
