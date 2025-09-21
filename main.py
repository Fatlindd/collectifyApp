import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from todo import main as todo_main  # Todo module

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")

# ------------------------------
# Inline CSS (formerly style.STYLE_CSS)
# ------------------------------
STYLE_CSS = """
<style>
:root {
  --card-bg: #ffffff;
  --card-border: #ececec;
  --card-shadow: 0 2px 10px rgba(0,0,0,0.06);
  --card-shadow-hover: 0 6px 20px rgba(0,0,0,0.10);
  --accent: #0ea5e9;
}
html, body, [data-testid="stAppViewContainer"] { background: #f7f8fb; }

.glance-wrap { margin-top: .25rem; }
.glance-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 18px;
}
@media (max-width: 1200px){ .glance-grid { grid-template-columns: repeat(8, 1fr); } }
@media (max-width: 768px){ .glance-grid { grid-template-columns: repeat(4, 1fr); } }

.glance-card {
  grid-column: span 6;
  display: flex; flex-direction: column;
  padding: 18px 18px 14px 18px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  box-shadow: var(--card-shadow);
  transition: box-shadow .2s ease, transform .08s ease;
  min-height: 126px;
}
.glance-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-1px); }
.glance-title { font-weight: 700; font-size: 20px; letter-spacing: .2px; display:flex; gap:.6rem; align-items:center;}
.glance-desc { color: #4b5563; margin-top: 8px; line-height: 1.45; min-height: 40px; }
.badge {
  height: 28px; width: 28px; border-radius: 8px;
  display:flex; align-items:center; justify-content:center;
  background: #eef6ff; color: #0b6bcb; font-size: 16px;
}
.card { background:#fff; border:1px solid #eee; border-radius:14px; box-shadow:var(--card-shadow); padding:16px; margin-bottom:16px; }
.card img { width:56px; height:56px; object-fit:contain; border-radius:10px; background:#fafafa; border:1px solid #f0f0f0;}
.card-title { font-weight:700; font-size:18px; margin-top:8px; }
.card-description { color:#4b5563; margin-top:6px; min-height:42px; }
.card-footer { margin-top:10px; }
.card-button {
  background: var(--accent); color: white; border: none; border-radius: 10px;
  padding: 8px 12px; cursor: pointer; font-weight: 600;
}
.card-button:hover { filter: brightness(0.95); }
</style>
"""
st.markdown(STYLE_CSS, unsafe_allow_html=True)

# ------------------------------
# Credentials
# ------------------------------
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

# ------------------------------
# Cross-page navigation helper
# ------------------------------
def go_to(page_name: str):
    st.session_state["__force_nav__"] = page_name
    st.rerun()

# ------------------------------
# Google Sheets Reader
# ------------------------------
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
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=self.scope
            )
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

# ------------------------------
# Category Page
# ------------------------------
def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.write(
        f"This page displays a curated list of **{target_category}** tools and resources. Browse the cards below."
    )
    st.divider()

    try:
        tools = reader.get_filtered_tools(target_category=target_category)
    except APIError as e:
        st.error("❌ Failed to fetch tools from Google Sheet.")
        st.exception(e)
        return

    search_query = st.text_input("Search by name", placeholder="Type a website/app name...").strip()
    filtered_tools = [t for t in tools if search_query.lower() in str(t.get("name", "")).lower()] if search_query else tools

    st.caption(f"Results: {len(filtered_tools)}")

    if filtered_tools:
        columns = st.columns([1, 1, 1])
        for idx, tool in enumerate(filtered_tools):
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
        st.info("ℹ️ No tools match your search.")

# ------------------------------
# Add Item Page
# ------------------------------
def render_add_item_page(reader):
    st.title("Add New Item")
    st.write("Use this page to contribute a new tool to the collection. Fill in the fields below.")
    st.divider()

    records = reader.get_all_records()
    categories = sorted(set(record.get("category", "").strip() for record in records if record.get("category", "").strip())) or ["Default"]

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
                st.error("❌ Failed to add prompt.")
                st.exception(e)
        else:
            st.warning("⚠️ Please fill in at least the Category and Name fields.")

# ------------------------------
# Prompts List
# ------------------------------
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

# ------------------------------
# Add Prompt
# ------------------------------
def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.write("Fill in the details to save a new ChatGPT prompt.")
    st.divider()

    description = st.text_area("Description")
    prompt = st.text_area("Prompt")

    if st.button("Add Prompt"):
        if description and prompt:
            new_prompt = {"description": description, "prompt": prompt}
            try:
                prompts_reader.append_new_item(new_prompt)
                st.success("✅ Prompt added successfully!")
            except Exception as e:
                st.error("❌ Failed to add prompt.")
                st.exception(e)
        else:
            st.warning("⚠️ Please fill in both the Description and Prompt fields.")

# ------------------------------
# Emoji set for Home cards (visual only)
# ------------------------------
EMOJI = {
    "ChatGPT Prompts": "💬",
    "Artificial Intelligence": "🤖",
    "Chrome Extensions": "🧩",
    "Django": "🗄️",
    "Free API Resources": "☁️",
    "FrontEnd Tools": "🎨",
    "Icons Website": "🖼️",
    "Programming Tools": "⚙️",
    "Python": "🐍",
    "React": "⚛️",
    "Useful Website": "🔗",
    "Useful Websites": "🔗",
    "Vscode Extensions": "🔌",
    "Web Design": "✏️",
    "Web Scraping": "🔎",
    "Youtube Videos": "▶️",
    "Add New ChatGPT Prompt": "➕",
    "Add New Item": "➕",
    "Todo App": "📝",
}

# Optional short blurbs (fallback if none found)
BLURB = {
    "ChatGPT Prompts": "Save and reuse high-impact prompts.",
    "Artificial Intelligence": "AI tools and workflows.",
    "Chrome Extensions": "Boost your browser productivity.",
    "Django": "Admin helpers, packages, snippets.",
    "Free API Resources": "Public APIs for prototypes.",
    "FrontEnd Tools": "UI kits, linters, inspectors.",
    "Icons Website": "Icon packs and search engines.",
    "Programming Tools": "CLIs, linters, formatters.",
    "Python": "Libraries, snippets, utilities.",
    "React": "Components, hooks, devtools.",
    "Useful Website": "Handy links & utilities.",
    "Useful Websites": "Handy links & utilities.",
    "Vscode Extensions": "Editor add-ons that help.",
    "Web Design": "Layouts, palettes, inspiration.",
    "Web Scraping": "Scrapers, parsers, proxies.",
    "Youtube Videos": "Learning and breakdowns.",
    "Add New ChatGPT Prompt": "Capture a new prompt.",
    "Add New Item": "Contribute a new tool.",
    "Todo App": "Plan, track and complete tasks.",
}

# ------------------------------
# Home (Modules at a Glance built from left navbar)
# ------------------------------
def home_page(nav_items_for_cards):
    st.title("Welcome to Collectify Tools")
    st.write("Discover a curated list of tools, websites, and AI resources. Use the sidebar or the cards below to jump into a module.")
    st.divider()

    st.subheader("Modules at a Glance")

    # Build card list from left navbar (exclude Home and divider)
    items = [i for i in nav_items_for_cards if i not in ("Home", "---")]
    if not items:
        st.info("No modules available yet.")
        return

    st.markdown('<div class="glance-wrap"><div class="glance-grid">', unsafe_allow_html=True)

    # Render each as a card with an "Open" button INSIDE the card
    for idx, title in enumerate(items):
        emoji = EMOJI.get(title, "🧰")
        desc = BLURB.get(title, f"Open the {title} module.")
        st.markdown(
            f"""
            <div class="glance-card">
                <div class="glance-title">
                    <span class="badge">{emoji}</span>
                    <span>{title}</span>
                </div>
                <div class="glance-desc">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Real Streamlit button that navigates
        st.button("Open", key=f"glance_open_{idx}", on_click=lambda t=title: go_to(t))

    st.markdown('</div></div>', unsafe_allow_html=True)

# ------------------------------
# Icon mapping helper for the sidebar (Bootstrap icon names)
# ------------------------------
def get_icon(page_name, mapping):
    for key, icon in mapping.items():
        if key.lower() == page_name.lower():
            return icon
    return "tools"

# ------------------------------
# Main
# ------------------------------
def main():
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    # Instantiate readers
    main_reader = CollectifySheetReader(creds=creds)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    # Categories from Sheet for dynamic menu
    try:
        records = main_reader.get_all_records()
        categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip()))
    except Exception as e:
        st.error("⚠️ Failed to load categories.")
        st.exception(e)
        categories = []

    # Page registry
    page_modules = {
        "Home": lambda: home_page(nav_items_for_cards=[]),  # placeholder, we fill it after menu is built
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
    }
    for category in categories:
        page_modules[category] = (lambda c=category: render_category_page(main_reader, c))

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
        "Useful Website": "link-45deg",
        "Useful Websites": "link-45deg",
        "Vscode Extensions": "plug",
        "Web Design": "brush",
        "Web Scraping": "search",
        "Youtube Videos": "youtube",
    }

    # Build menu
    menu_keys_top = ["Home", "Add New ChatGPT Prompt", "Todo App", "---", "ChatGPT Prompts"]
    menu_keys_bottom = categories
    menu_keys = menu_keys_top + menu_keys_bottom
    menu_icons = [get_icon(key, icon_mapping) for key in menu_keys]

    with st.sidebar:
        selected = option_menu("Useful Tools", menu_keys, icons=menu_icons, default_index=0)

    # Rebuild Home now that we know nav items
    page_modules["Home"] = lambda: home_page(menu_keys)

    # Allow Home card clicks to override selection
    if "__force_nav__" in st.session_state:
        selected = st.session_state.pop("__force_nav__")

    if selected != "---":
        # If a target isn't in page_modules but exists as a dynamic category, render it
        if selected not in page_modules and selected in categories:
            render_category_page(main_reader, selected)
        else:
            page_modules.get(selected, lambda: st.error("Page not found"))()

if __name__ == "__main__":
    main()
