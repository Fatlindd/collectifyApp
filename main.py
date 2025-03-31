import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from style import STYLE_CSS  # Import your custom CSS

from todo import main as todo_main

# Set Streamlit layout to wide mode
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")


class CollectifySheetReader:
    """
    A class to read, filter, and update data from a specified worksheet
    in the "Collectify" spreadsheet.
    """
    SPREADSHEET_TITLE = "Collectify"

    # Updated __init__: added optional creds parameter for secrets
    def __init__(self, worksheet_name="collectify_data", creds=None, scope=None):
        """
        Parameters:
            worksheet_name (str): The worksheet name to access.
            creds (str): JSON string from Streamlit Secrets (if available)
            scope (list): OAuth scopes. Writing requires the spreadsheets scope.
        """
        if scope is None:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/spreadsheets"  # Needed for writing
            ]
        self.worksheet_name = worksheet_name
        self.scope = scope
        # Pass the creds to _authorize_client
        self.client = self._authorize_client(creds)
        self.worksheet = self._get_worksheet()

    # Updated _authorize_client: now checks if creds provided via st.secrets are available.
    def _authorize_client(self, creds):
        # If credentials are provided (from secrets), use them.
        if creds:
            # st.secrets["gcp_service_account"] is expected to be a dict (from TOML)
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=self.scope)
        else:
            # Fallback for local development using the local JSON file.
            credentials = Credentials.from_service_account_file("collectify_credentials.json", scopes=self.scope)
        return gspread.authorize(credentials)

    def _get_worksheet(self):
        spreadsheet = self.client.open(self.SPREADSHEET_TITLE)
        return spreadsheet.worksheet(self.worksheet_name)

    def get_all_records(self):
        """Return all rows as a list of dictionaries (using the header row as keys)."""
        return self.worksheet.get_all_records()

    def get_filtered_tools(self, target_category, category_field="category", output_mapping=None):
        """
        Filter rows based on target_category (in the specified category_field)
        and return a list of dictionaries with the desired output keys.
        """
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
        """
        Append a new item (a dict) as a row to the worksheet.
        The new row is built based on the header order.
        """
        headers = self.worksheet.row_values(1)
        new_row = [item.get(header, "") for header in headers]
        self.worksheet.append_row(new_row)


def render_category_page(reader, target_category):
    """
    Renders a page that displays tools for the given category in a card layout using three columns.
    """
    st.title(f"{target_category} Tools")
    st.write(
        f"This page displays a curated list of {target_category} tools and resources. Browse through the cards below and click on any tool to learn more.")
    st.divider()

    tools = reader.get_filtered_tools(target_category=target_category)
    if tools:
        columns = st.columns([1, 1, 1])
        for idx, tool in enumerate(tools):
            col = columns[idx % 3]  # Cycle through the columns
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
        st.write("No tools available for this category.")


def render_add_item_page(reader):
    """
    Renders a page with input fields to add a new item.
    The inputs are arranged as:
      - Row 1: Category (dropdown) and Name (text input)
      - Row 2: Description field (full width)
      - Row 3: Logo URL and Store Link in two columns
      - Row 4: Button Name and Used (dropdown) in two columns
    """
    st.title("Add New Item")
    st.write(
        "Use this page to add a new tool to our collection. Fill out the details below and contribute to our resource list.")
    st.divider()

    # Retrieve distinct categories from the sheet for the dropdown.
    records = reader.get_all_records()
    categories = sorted(
        set(record.get("category", "").strip() for record in records if record.get("category", "").strip()))
    if not categories:
        categories = ["Default"]

    # Row 1: Category and Name in two columns.
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Select Category", options=categories)
    with col2:
        name = st.text_input("Name")

    # Row 2: Description field (full width).
    description = st.text_area("Description")

    # Row 3: Logo URL and Store Link in two columns.
    col3, col4 = st.columns(2)
    with col3:
        logo_url = st.text_input("Logo URL")
    with col4:
        store_link = st.text_input("Store Link")

    # Row 4: Button Name and Used in two columns.
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
                st.success("New item added successfully!")
            except Exception as e:
                st.error(f"Error adding new item: {e}")
        else:
            st.error("Please fill in at least the Category and Name fields.")


def render_chatgpt_prompts_page(prompts_reader):
    """
    Renders a page that displays ChatGPT prompts.
    For each row, the description is shown as text and the prompt as a code block.
    """
    st.title("ChatGPT Prompts")
    st.write(
        "This page displays a collection of ChatGPT prompts. Review the description below each entry and see the prompt details in the code block.")
    st.divider()

    records = prompts_reader.get_all_records()
    for row in records:
        st.write("📌 " + row.get("description", ""))
        st.code(row.get("prompt", ""))
        st.divider()


def render_add_chatgpt_prompt_page(prompts_reader):
    """
    Renders a page with input fields to add a new ChatGPT prompt.
    The user fills in:
      - Description
      - Prompt
    The new prompt is appended to the "ChatGPT Prompts" sheet.
    """
    st.title("Add New ChatGPT Prompt")
    st.write("Use this page to add a new ChatGPT prompt to our collection. Fill in the description and prompt below.")
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
                st.success("New ChatGPT prompt added successfully!")
            except Exception as e:
                st.error(f"Error adding new prompt: {e}")
        else:
            st.error("Please fill in both the Description and Prompt fields.")


def home_page():
    st.title("Welcome to Collectify Tools")
    st.write(
        "This website is designed to help you discover a wide range of online tools, resources, and websites curated for different needs. Use the sidebar to browse various categories, explore ChatGPT prompts, or contribute by adding a new item.")
    st.divider()
    st.write(
        """
        **About This App** 🚀✨

        I built this web app as a personal project to support my journey as a programmer and boost my productivity at work. It serves as a centralized hub of hand-picked resources and innovative tools that help me learn new techniques, solve challenging problems, and stay ahead in the fast-paced tech world.

        Every tool and prompt has been carefully selected to streamline my workflow, enhance my skills, and ultimately make my daily tasks smoother and more efficient.

        **Welcome to my productivity toolkit!** 💡👨‍💻
        """
    )



def get_icon(page_name, mapping):
    """
    Helper function that performs case-insensitive matching of page_name against
    the keys in the mapping and returns the corresponding icon. If no match is found,
    returns a default icon.
    """
    for key, icon in mapping.items():
        if page_name.lower() == key.lower():
            return icon
    return "tools"


def main():
    # Inject the custom CSS style into the app.
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    # Load credentials from Streamlit secrets if available; otherwise fallback to local file.
    # This line fetches the secret as a dict (or returns None).
    creds = st.secrets.get("gcp_service_account", None)

    # Instantiate the reader for the main sheet ("collectify_data").
    main_reader = CollectifySheetReader(creds=creds)
    # Instantiate a reader for the "ChatGPT Prompts" sheet.
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    # Get distinct categories from the main sheet.
    records = main_reader.get_all_records()
    categories = sorted(
        set(record.get("category", "").strip() for record in records if record.get("category", "").strip())
    )

    # Create a dictionary of page modules.
    # We'll add a special key "---" to represent the divider.
    page_modules = {
        "Home": home_page,
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "---": lambda: None,  # Divider does nothing
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
        "Todo App": lambda: todo_main(creds)
    }

    # Dynamically create a page for each category from the main sheet.
    for cat in categories:
        page_modules[cat] = lambda category=cat: render_category_page(main_reader, category)

    # Define an icon mapping based on page module names.
    icon_mapping = {
        "Home": "house",
        "Add New Item": "plus-square",
        "Add New ChatGPT Prompt": "plus-circle",
        "---": "dash",  # Icon for the divider (not really used)
        "ChatGPT Prompts": "chat-dots",
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
        "Youtube Videos": "youtube",
        "Todo App": "list-task"
    }

    # Build the final sidebar menu order:
    menu_keys_top = ["Home", "Add New Item", "Add New ChatGPT Prompt", "Todo App", "---", "ChatGPT Prompts"]
    menu_keys_bottom = categories  # dynamic categories
    menu_keys = menu_keys_top + menu_keys_bottom

    # Generate icons for each menu key.
    menu_icons = [get_icon(key, icon_mapping) for key in menu_keys]

    # Sidebar menu with dynamic page modules and icons.
    with st.sidebar:
        selected = option_menu(
            "Useful Tools",
            menu_keys,
            icons=menu_icons,
            default_index=0
        )

    # Render the selected page (if it's the divider "---", do nothing).
    if selected != "---":
        page_modules[selected]()


if __name__ == "__main__":
    main()
