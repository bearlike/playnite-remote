#!/usr/bin/env python3
import glob
import os
import math

from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.colored_header import colored_header
from streamlit_extras.bottom_container import bottom
from bson.objectid import ObjectId
import streamlit_shadcn_ui as ui
import streamlit as st
from PIL import Image
import pymongo

import constants
from utils import (
    parse_url_file,
    find_image_for_uuid,
    execute_command,
    display_pagination_controls,
)


st.set_page_config(
    page_title="App Launcher",
    page_icon="🚀",
    layout="wide",
)

# TODO: Add search functionality and filters.

client = pymongo.MongoClient(constants.MONGO_URI)
db = client["launcher"]
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
                "command": f"start {url}",
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


def display_applications(column_size: int = 6, row_size: int = 4) -> None:
    """Function to display registered applications in a card layout"""
    # Hide the default Streamlit image fullscreen button
    hide_img_fs = """
    <style>
    button[title="View fullscreen"]{
        visibility: hidden;}
    </style>
    """
    page_limit = column_size * row_size
    start_page = int(st.query_params.get("page", 1))
    st.markdown(hide_img_fs, unsafe_allow_html=True)

    apps = list(apps_collection.find())
    total_apps = len(apps)
    sdx = (start_page - 1) * page_limit
    edx = start_page * page_limit
    apps = apps[sdx:edx]

    if not apps:
        st.warning("No applications are registered yet.")
        return

    # Define how many cards per row
    for i in range(0, len(apps), column_size):
        cols = st.columns(column_size)
        for j in range(column_size):
            if i + j < len(apps):
                app = apps[i + j]
                with cols[j]:
                    display_card(app, element_key=i + j)

    # Pagination logic
    if total_apps > 0:
        total_pages = math.ceil(total_apps / page_limit)
        with bottom():
            display_pagination_controls(start_page, total_pages)


def display_card(app: dict, element_key: int) -> None:
    with st.container(border=True):
        card_image_path = app.get("picture", None)

        if card_image_path:
            # Resize image to 600x800
            card_image = Image.open(card_image_path).resize((300, 400))
        else:
            card_image = constants.FALLBACK_POSTER

        st.image(card_image, use_column_width=True)

        card_title = app.get("title", "").ljust(48, "\u200B")
        card_title = card_title.replace(
            "\u200B", "<span style='color: transparent;'>-</span>"
        )
        card_subtitle = app.get("subtitle", "")
        st.markdown(f"<strong>{card_title}</strong>", unsafe_allow_html=True)

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
                    key=element_key,
                    use_container_width=True,
                    type="primary",
                    help=helper_text,
                ):
                    execute_command(app.get("command", ""), app.get("cwd", ""))

            with button_col2:
                if st.button(
                    ":pencil2:",
                    key=f"edit{element_key}",
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
    footer_col = st.columns([3, 1])
    footer_col[0].caption(
        "Made with ❤️ by [Krishnakanth Alagiri](https://github.com/bearlike)."
    )
    footer_col[1].caption(
        "Issues or suggestions? [Open an issue](https://github.com/bearlike/playnite-remote/issues)."
    )


def driver() -> None:
    st.header("Krishna's Cooked Launcher", divider="rainbow", anchor=False)
    selected_tab = ui.tabs(
        options=[
            "View Applications",
            "Register New Application",
            "Import Playnite Shortcuts",
        ],
        default_value="View Applications",
        key="main_tabs",
    )

    # Page logic
    if selected_tab == "View Applications":
        display_applications()

    elif selected_tab == "Register New Application":
        add_application()

    elif selected_tab == "Import Playnite Shortcuts":
        playnite_import_page()

    footer()


if __name__ == "__main__":
    driver()
