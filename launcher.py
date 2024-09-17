#!/usr/bin/env python3
from typing import Optional
import configparser
import glob
import os

from streamlit_extras.stylable_container import stylable_container
from bson.objectid import ObjectId
import streamlit as st
from PIL import Image
import pymongo

import constants


st.set_page_config(
    page_title="App Launcher",
    page_icon="🚀",
    layout="wide",
)

# TODO: Add search functionality and filters.

client = pymongo.MongoClient(constants.MONGO_URI)
db = client["launcher1"]
apps_collection = db["applications"]


@st.dialog("Edit Application")
def edit_application_by_id(app_id: str):
    """
    Function to edit an existing application by its MongoDB _id.

    Args:
        app_id (str): The MongoDB _id of the application to be edited.
    """
    app_object_id = ObjectId(app_id)
    app = apps_collection.find_one({"_id": app_object_id})

    if not app:
        st.error(f"Application with _id {app_id} not found.")
        return

    # Prefill the form with existing data
    picture = st.text_input("Picture URL", app.get("picture", ""))
    title = st.text_input("Title", app.get("title", ""))
    subtitle = st.text_input("Subtitle", app.get("subtitle", ""))
    cwd = st.text_input("Current Working Directory", app.get("cwd", ""))
    command = st.text_input("Command", app.get("command", ""))

    # Submit button to save the changes
    if st.button("Save Changes", use_container_width=True, type="primary"):
        # Update the application in MongoDB
        updated_app = {
            "picture": picture,
            "title": title,
            "subtitle": subtitle,
            "cwd": cwd,
            "command": command,
        }
        # Perform the update in MongoDB
        apps_collection.update_one({"_id": app_object_id}, {"$set": updated_app})
        st.toast(f"Application '{title}' has been updated successfully!")


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


def scan_and_import_playnite_shortcuts() -> None:
    """Function to scan the Playnite shortcuts folder and import them
    into MongoDB
    """
    shortcut_dir = constants.PLAYNITE_SHORTCUTS_DIR
    url_files = glob.glob(os.path.join(shortcut_dir, "*.url"))

    total_files = len(url_files)

    if total_files == 0:
        st.warning("No Playnite shortcuts found.")
        return

    st.info(f"Found {total_files} Playnite shortcut(s). Starting scan...")

    progress_bar = st.progress(0)
    log_placeholder = st.empty()

    for idx, file_path in enumerate(url_files):
        file_name = os.path.basename(file_path).replace(".url", "")

        # Parse the .url file
        icon_file, url = parse_url_file(file_path)

        if url and icon_file:
            # Extract UUID from the URL
            uuid = url.split("/")[-1]  # Extract UUID from the URL path

            # Find a suitable image in the Playnite library
            selected_image = find_image_for_uuid(uuid)

            # Prepare the final application data
            app_data = {
                "picture": selected_image,
                "title": file_name,
                "subtitle": "Playnite",
                "cwd": None,
                "command": url,
            }

            # Insert into MongoDB
            apps_collection.insert_one(app_data)

            # Log progress
            log_placeholder.text(f"Imported: {file_name} ({idx+1}/{total_files})")

        else:
            log_placeholder.text(f"Skipped (invalid .url file): {file_name}")

        # Update progress bar
        progress_bar.progress((idx + 1) / total_files)

    st.success("Scan complete! All Playnite shortcuts have been imported.")


def playnite_import_page() -> None:
    """Page for scanning and importing Playnite shortcuts"""
    with st.container(border=True):
        st.subheader("Import Playnite Shortcuts ⏬")

        st.write(
            "This tool allows you to import Playnite URL shortcuts from "
            f"`{constants.PLAYNITE_SHORTCUTS_DIR}`."
        )

        if st.button("Start Scan 🔎", type="primary", use_container_width=True):
            scan_and_import_playnite_shortcuts()


def execute_command(command: str, cwd: str) -> None:
    """Function to execute a command in the given directory"""
    try:
        to_run = ""
        if cwd:
            to_run += f"cd {cwd} &&"
        if command and command.startswith("playnite://"):
            to_run += f"start {command}"
        elif command:
            to_run += f"{command}"

        to_run = to_run.strip()
        os.system(to_run)
        st.toast(f"Executed: `{command}`", icon="✅")

    except Exception as e:
        st.toast(f"Error executing command: `{str(e)}`", icon="❌")


def display_applications() -> None:
    """Function to display registered applications in a card layout"""
    # Hide the default Streamlit image fullscreen button
    hide_img_fs = """
    <style>
    button[title="View fullscreen"]{
        visibility: hidden;}
    </style>
    """

    st.markdown(hide_img_fs, unsafe_allow_html=True)
    apps = list(apps_collection.find())  # Fetch all applications

    if not apps:
        st.warning("No applications are registered yet.")
        return

    # Define how many cards per row
    column_size = 6
    for i in range(0, len(apps), column_size):
        cols = st.columns(column_size)
        for j in range(column_size):
            if i + j < len(apps):
                app = apps[i + j]

                with cols[j].container(border=True):
                    card_image_path = app.get("picture", None)

                    if card_image_path:
                        # Resize image to 600x800
                        card_image = Image.open(card_image_path).resize((600, 800))
                    else:
                        card_image = constants.FALLBACK_POSTER

                    st.image(card_image, use_column_width=True)

                    card_title = app.get("title", "")
                    card_subtitle = app.get("subtitle", "")
                    st.markdown(f"**{card_title}**")

                    helper_text = (
                        f"- **Platform:** {card_subtitle}\n"
                        + f"- **Current Working Directory (CWD):** {app.get('cwd', 'N/A')}\n"
                        + f"- **Command:** `{app.get('command', 'N/A')}`"
                    )
                    with stylable_container(
                        key="green_button",
                        css_styles="""
                            [data-testid="stHorizontalBlock"] {
                                gap: 0rem;
                            }
                            [data-testid="stBaseButton-primary"],[data-testid="stBaseButton-secondary"] {
                                border-radius: 0rem;
                            }
                            """,
                    ):
                        button_col1, button_col2 = st.columns([4, 1])
                        with button_col1:
                            if st.button(
                                "Run",
                                key=i + j,
                                use_container_width=True,
                                type="primary",
                                help=helper_text,
                            ):
                                execute_command(
                                    app.get("command", ""), app.get("cwd", "")
                                )

                        with button_col2:
                            if st.button(
                                ":pencil2:",
                                key=f"edit{i + j}",
                                use_container_width=True,
                            ):
                                edit_application_by_id(str(app["_id"]))


def add_application() -> None:
    """Function to add a new application to the database"""
    with st.form("new_app_form"):
        st.subheader("Register New Application 🌸")
        picture = st.text_input("Picture URL", None)
        title = st.text_input("Title")
        subtitle = st.text_input("Subtitle")
        cwd = st.text_input("Current Working Directory")
        command = st.text_input("Command")

        submitted = st.form_submit_button(
            "Register Application", use_container_width=True, type="primary"
        )
        if submitted:
            new_app = {
                "picture": picture,
                "title": title,
                "subtitle": subtitle,
                "cwd": cwd,
                "command": command,
            }
            apps_collection.insert_one(new_app)
            st.success("Application registered successfully!")


def footer() -> None:
    st.divider()
    st.caption(
        "Issues or suggestions? [Open an issue](https://github.com/bearlike/playnite-remote/issues)."
    )
    st.caption("Made with ❤️ by [Krishnakanth Alagiri](https://github.com/bearlike).")


def driver() -> None:
    st.title("Krishna's Cooked Launcher")

    tab1, tab2, tab3 = st.tabs(
        ["View Applications", "Register New Application", "Import Playnite Shortcuts"]
    )

    # Page logic
    with tab1:
        display_applications()
    with tab2:
        add_application()
    with tab3:
        playnite_import_page()

    footer()


if __name__ == "__main__":
    driver()
