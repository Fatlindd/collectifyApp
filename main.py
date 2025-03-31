import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials
from style import STYLE_CSS  # Your custom CSS
from todo import main as todo_main  # Import Todo App logic

# Set global layout for the entire app
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")


class CollectifySheetReader:
    SPREADSHEET_TITLE = "Collectify"

    def __init__(self, worksheet_name="collectify_data", creds=None, scope=None):
        if scope is None:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/spreadsheets"
            ]
        self.worksheet_name = worksheet_name
        self.scope = scope
        self.client = self._authorize_client(creds)
        self.worksheet = self._get_worksheet()

    def _authorize_client(self, creds):
        try:
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=self.scope)
            return gspread.authorize(credentials)
        except Exception as e:
            st.error("❌ Google Sheets authorization failed.")
            st.exception(e)
            st.stop()

    def _get_worksheet(self):
        try:
            spreadsheet = self.client.open(self.SPREADSHEET_TITLE)
            return spreadsheet.worksheet(self.worksheet_name)
        except APIError as e:
            st.error(f"❌ Worksheet '{self.worksheet_name}' could not be accessed.")
            st.exception(e)
            st.stop()

    def get_all_records(self):
        try:
            return self.worksheet.get_all_records()
        except APIError as e:
            st.error("❌ Error reading records from Google Sheets.")
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
        filtered_tools = [
            {out_key: row.get(sheet_col, "") for out_key, sheet_col in output_mapping.items()}
            for row in data if row.get(category_field) == target_category
        ]
        return filtered_tools

    def append_new_item(self, item):
        try:
            headers = self.worksheet.row_values(1)
            new_row = [item.get(header, "") for header in headers]
            self.worksheet.append_row(new_row)
        except Exception as e:
            st.error("❌ Failed to append new item.")
            st.exception(e)


def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.write(f"Explore curated tools under **{target_category}**.")
    st.divider()

    tools = reader.get_filtered_tools(target_category)
    if tools:
        columns = st.columns(3)
        for idx, tool in enumerate(tools):
            col = columns[idx % 3]
            with col:
                st.markdown(f"""
                    <div class="card">
                        <img src="{tool['logo_url']}" alt="{tool['name']} logo">
                        <div class="card-title">{tool['name']}</div>
                        <div class="card-description">{tool['description']}</div>
                        <div class="card-footer">
                            <a href="{tool['store_link']}" target="_blank">
                                <button class="card-button">{tool['button_name']}</button>
                            </a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No tools found for this category.")


def render_add_item_page(reader):
    st.title("Add New Item")
    st.write("Fill out the form to contribute a new tool.")
    st.divider()

    records = reader.get_all_records()
    categories = sorted(set(record.get("category", "").strip() for record in records if record.get("category", "").strip()))
    if not categories:
        categories = ["Default"]

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", options=categories)
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
            item = {
                "category": category,
                "name": name,
                "description": description,
                "logo_url": logo_url,
                "store_link": store_link,
                "button_name": button_name,
                "used": used
            }
            reader.append_new_item(item)
            st.success("✅ New item added!")
        else:
            st.error("Please provide both Category and Name.")


def render_chatgpt_prompts_page(prompts_reader):
    st.title("ChatGPT Prompts")
    st.write("Browse helpful prompts for ChatGPT below.")
    st.divider()

    records = prompts_reader.get_all_records()
    for row in records:
        st.write("📌 " + row.get("description", ""))
        st.code(row.get("prompt", ""))
        st.divider()


def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.divider()

    description = st.text_area("Description")
    prompt = st.text_area("Prompt")

    if st.button("Add Prompt"):
        if description and prompt:
            prompts_reader.append_new_item({
                "description": description,
                "prompt": prompt
            })
            st.success("✅ Prompt added!")
        else:
            st.error("Both fields are required.")


def home_page():
    st.title("Welcome to Collectify Tools")
    st.markdown("""
    This app helps you organize and explore productivity tools and ChatGPT prompts.  
    Navigate with the sidebar to explore or contribute content.
    """)
    st.divider()
    st.markdown("""
    **Why I Built This** 🧠  
    I created Collectify to manage and share the best tools I use daily as a developer.  
    From extensions to APIs to prompts — it's all here.  
    """)


def get_icon(page_name, mapping):
    for key, icon in mapping.items():
        if page_name.lower() == key.lower():
            return icon
    return "tools"


def main():
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    creds = st.secrets.get("gcp_service_account", None)

    main_reader = CollectifySheetReader(creds=creds)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    records = main_reader.get_all_records()
    categories = sorted(set(record.get("category", "").strip() for record in records if record.get("category", "").strip()))

    page_modules = {
        "Home": home_page,
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
        "Todo App": lambda: todo_main(creds)
    }

    for cat in categories:
        page_modules[cat] = lambda category=cat: render_category_page(main_reader, category)

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

    menu_keys_top = ["Home", "Add New Item", "Add New ChatGPT Prompt", "Todo App", "---", "ChatGPT Prompts"]
    menu_keys = menu_keys_top + categories
    menu_icons = [get_icon(key, icon_mapping) for key in menu_keys]

    with st.sidebar:
        selected = option_menu("Useful Tools", menu_keys, icons=menu_icons, default_index=0)

    if selected != "---":
        page_modules[selected]()


if __name__ == "__main__":
    main()
