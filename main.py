import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from style import STYLE_CSS  # Custom CSS file
from todo import main as todo_main  # Todo module

# Set page configuration
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")

# Inject custom styles
st.markdown(STYLE_CSS, unsafe_allow_html=True)

# Load credentials from secrets
try:
    creds_info = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(dict(creds_info), scopes=scopes)
except Exception as e:
    st.error("❌ Failed to load Google credentials.")
    st.exception(e)
    st.stop()


class CollectifySheetReader:
    SPREADSHEET_TITLE = "Collectify"

    def __init__(self, worksheet_name="collectify_data", creds=None):
        self.worksheet_name = worksheet_name
        self.creds = creds or creds_info
        self.scope = scopes
        self.client = self._authorize_client()
        self.worksheet = self._get_worksheet()

    def _authorize_client(self):
        try:
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=self.scope)
            return gspread.authorize(credentials)
        except Exception as e:
            st.error("❌ Could not authorize Google Sheets client.")
            st.exception(e)
            st.stop()

    def _get_worksheet(self):
        try:
            spreadsheet = self.client.open(self.SPREADSHEET_TITLE)
            return spreadsheet.worksheet(self.worksheet_name)
        except APIError as e:
            st.error("❌ Unable to open the worksheet.")
            st.exception(e)
            st.stop()

    def get_all_records(self):
        try:
            return self.worksheet.get_all_records()
        except APIError as e:
            st.error("⚠️ Failed to load data from Google Sheet.")
            st.exception(e)
            return []

    def get_filtered_tools(self, target_category, category_field="category", output_mapping=None):
        if output_mapping is None:
            output_mapping = {
                "name": "name",
                "description": "description",
                "logo_url": "logo_url",
                "store_link": "store_link",
                "button_name": "button_name"
            }
        data = self.get_all_records()
        filtered = [
            {out_key: row.get(sheet_col, "") for out_key, sheet_col in output_mapping.items()}
            for row in data if row.get(category_field) == target_category
        ]
        return filtered

    def append_new_item(self, item):
        try:
            headers = self.worksheet.row_values(1)
            new_row = [item.get(header, "") for header in headers]
            self.worksheet.append_row(new_row)
        except APIError as e:
            st.error("❌ Failed to append new item to the sheet.")
            st.exception(e)


def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.write(
        f"This page displays a curated list of {target_category} tools and resources. Browse through the cards below and click on any tool to learn more."
    )
    st.divider()

    try:
        tools = reader.get_filtered_tools(target_category=target_category)
    except APIError as e:
        st.error("❌ Failed to fetch tools from Google Sheet.")
        st.exception(e)
        return

    if tools:
        columns = st.columns([1, 1, 1])
        for idx, tool in enumerate(tools):
            col = columns[idx % 3]
            with col:
                st.markdown(f"""
                    <div class="card">
                        <img src="{tool.get('logo_url', '')}" alt="{tool.get('name', 'Tool')} logo">
                        <div class="card-title">{tool.get('name', 'Untitled Tool')}</div>
                        <div class="card-description">{tool.get('description', 'No description available.')}</div>
                        <div class="card-footer">
                            <a href="{tool.get('store_link', '#')}" target="_blank">
                                <button class="card-button">{tool.get('button_name', 'Open')}</button>
                            </a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No tools available for this category.")


# ----------------------------------------
# Add a new item to the tool sheet
# ----------------------------------------

def render_add_item_page(reader):
    st.title("Add New Item")
    st.write("Use this page to contribute a new tool to the collection. Fill in the fields below.")
    st.divider()

    # ✅ Instead: load categories directly without caching
    records = reader.get_all_records()
    categories = sorted(
        set(record.get("category", "").strip() for record in records if record.get("category", "").strip())
    )
    if not categories:
        categories = ["Default"]

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Select Category", options=categories)
    with col2:
        name = st.text_input("Name")

    description = st.text_area("Description")

    col3, col4 = st.columns(2)
    with col3:
        logo_url = st.text_input("Logo URL")
    with col4:
        store_link = st.text_input("Store Link")

    col5, col6 = st.columns(2)
    with col5:
        button_name = st.text_input("Button Name")
    with col6:
        used = st.selectbox("Used", options=["Yes", "No"])

    if st.button("Add Item"):
        if name and category:
            new_item = {
                "category": category,
                "name": name,
                "description": description,
                "logo_url": logo_url,
                "store_link": store_link,
                "button_name": button_name,
                "used": used
            }
            try:
                reader.append_new_item(new_item)
                st.success("✅ New item added successfully!")
            except Exception as e:
                st.error("❌ Failed to add item.")
                st.exception(e)
        else:
            st.warning("⚠️ Please fill in at least the Category and Name fields.")


# ----------------------------------------
# Show ChatGPT prompts page
# ----------------------------------------
def render_chatgpt_prompts_page(prompts_reader):
    st.title("ChatGPT Prompts")
    st.write("Browse useful ChatGPT prompts with short descriptions and pre-filled content.")
    st.divider()

    try:
        records = prompts_reader.get_all_records()
    except APIError as e:
        st.error("❌ Failed to load prompts.")
        st.exception(e)
        return

    if records:
        for row in records:
            st.write("📌 " + row.get("description", ""))
            st.code(row.get("prompt", ""))
            st.divider()
    else:
        st.info("ℹ️ No prompts found.")


# ----------------------------------------
# Add new ChatGPT prompt
# ----------------------------------------
def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.write("Fill in the details to save a new ChatGPT prompt.")
    st.divider()

    description = st.text_area("Description")
    prompt = st.text_area("Prompt")

    if st.button("Add Prompt"):
        if description and prompt:
            new_prompt = {
                "description": description,
                "prompt": prompt
            }
            try:
                prompts_reader.append_new_item(new_prompt)
                st.success("✅ Prompt added successfully!")
            except Exception as e:
                st.error("❌ Failed to add prompt.")
                st.exception(e)
        else:
            st.warning("⚠️ Please fill in both the Description and Prompt fields.")


# ----------------------------------------
# Homepage
# ----------------------------------------
def home_page():
    st.title("Welcome to Collectify Tools")
    st.write(
        "Discover a curated list of tools, websites, and AI resources. Use the sidebar to explore categories, add your own, or check out ChatGPT prompts."
    )
    st.divider()
    st.markdown(
        """
        ### 🚀 About This App

        I built this platform to centralize the tools and prompts that make my development journey smoother and more productive. Whether you're a student, developer, or tech enthusiast, this toolkit is designed to help you learn faster and work smarter.

        **Feel free to explore and contribute!** 💡
        """
    )

def get_icon(page_name, mapping):
    """
    Returns the icon for a given page using case-insensitive lookup.
    If not found, defaults to 'tools'.
    """
    for key, icon in mapping.items():
        if key.lower() == page_name.lower():
            return icon
    return "tools"


def main():
    # Inject custom styles
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    # Load credentials from Streamlit secrets
    try:
        creds_info = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(dict(creds_info), scopes=scopes)
    except Exception as e:
        st.error("❌ Failed to load credentials from secrets.")
        st.exception(e)
        st.stop()

    # Instantiate readers
    main_reader = CollectifySheetReader(creds=creds)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    # Get distinct categories for dynamic menu
    try:
        records = main_reader.get_all_records()
        categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip()))
    except Exception as e:
        st.error("⚠️ Failed to load categories.")
        st.exception(e)
        categories = []

    # Page routing
    page_modules = {
        "Home": home_page,
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds),
        "---": lambda: None,  # Just a divider
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader)
    }

    for category in categories:
        page_modules[category] = lambda category=category: render_category_page(main_reader, category)

    # Icon mapping for sidebar
    icon_mapping = {
        "Home": "house",
        "Add New Item": "plus-square",
        "Add New ChatGPT Prompt": "plus-circle",
        "---": "dash",
        "ChatGPT Prompts": "chat-dots",
        "Todo App": "list-task",
        "Artificial Intelligence": "robot",
        "Chrome Extensions": "puzzle",
        "Django": "server",
        "Free API Resources": "cloud",
        "FrontEnd Tools": "palette",
        "Icons Website": "image",
        "Programming Tools": "gear",
        "Python": "terminal",
        "React": "code-slash",
        "Useful Websites": "link-45deg",
        "VSCode Extensions": "plug",
        "Web Design": "brush",
        "Web Scraping": "search",
        "Youtube Videos": "youtube"
    }

    # Menu construction
    menu_keys_top = ["Home", "Add New Item", "Add New ChatGPT Prompt", "Todo App", "---", "ChatGPT Prompts"]
    menu_keys_bottom = categories
    menu_keys = menu_keys_top + menu_keys_bottom
    menu_icons = [get_icon(key, icon_mapping) for key in menu_keys]

    with st.sidebar:
        selected = option_menu(
            "Useful Tools",
            menu_keys,
            icons=menu_icons,
            default_index=0
        )

    # Page execution
    if selected != "---":
        page_modules[selected]()


if __name__ == "__main__":
    main()
