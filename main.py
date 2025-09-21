import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from datetime import datetime, timezone
from todo import main as todo_main

# -----------------------------
# Inline CSS (STYLE_CSS)
# -----------------------------
STYLE_CSS = """
/* Global page tweaks */
body, .stApp { background: #f7f9fc; }
.block-container { padding-top: 1.5rem; }

/* Header */
.home-header { margin-bottom: 8px; }
.home-title { font-size: 40px; font-weight: 800; margin: 0; }
.home-subtitle { font-size: 16px; color: #5f6368; margin: 6px 0 0; }

/* Metric cards */
.metric-card {
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  margin-bottom: 12px;
}
.metric-value { font-size: 36px; font-weight: 700; line-height: 1; }
.metric-label { font-size: 14px; color: #5f6368; margin-top: 6px; }

/* Module cards */
.module-card {
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}
.module-title { font-weight: 700; font-size: 18px; }
.module-desc { color: #5f6368; font-size: 14px; }

/* Tool cards (category pages) */
.card {
  border: 1px solid #eef0f3;
  border-radius: 16px;
  padding: 16px;
  background: #fff;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.card img { width: 64px; height: 64px; object-fit: contain; }
.card-title { font-weight: 700; margin-top: 8px; font-size: 16px; }
.card-description { color: #5f6368; font-size: 14px; margin: 8px 0 12px; }
.card-footer .card-button {
  background: #0ea5e9;
  color: #fff;
  border: none;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
}
.card-footer .card-button:hover { opacity: .9; }
"""

# -----------------------------
# Page configuration and styles
# -----------------------------
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")
st.markdown(STYLE_CSS, unsafe_allow_html=True)

# -----------------------------
# Auth
# -----------------------------
try:
    creds_info = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(dict(creds_info), scopes=scopes)
except Exception as e:
    st.error("Failed to load Google credentials.")
    st.exception(e)
    st.stop()


# -----------------------------
# Sheets helper
# -----------------------------
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
            st.error("Could not authorize Google Sheets client.")
            st.exception(e)
            st.stop()

    def _get_worksheet(self):
        try:
            spreadsheet = self.client.open(self.SPREADSHEET_TITLE)
            return spreadsheet.worksheet(self.worksheet_name)
        except APIError as e:
            st.error("Unable to open the worksheet.")
            st.exception(e)
            st.stop()

    def get_all_records(self):
        try:
            return self.worksheet.get_all_records()
        except APIError as e:
            st.error("Failed to load data from Google Sheet.")
            st.exception(e)
            return []

    def get_filtered_tools(self, target_category, category_field="category", output_mapping=None):
        if output_mapping is None:
            output_mapping = {
                "name": "name",
                "description": "description",
                "logo_url": "logo_url",
                "store_link": "store_link",
                "button_name": "button_name",
                "used": "used",
            }
        data = self.get_all_records()
        filtered = [
            {out_key: row.get(sheet_col, "") for out_key, sheet_col in output_mapping.items()}
            for row in data
            if row.get(category_field) == target_category
        ]
        return filtered

    def append_new_item(self, item):
        try:
            headers = self.worksheet.row_values(1)
            new_row = [item.get(header, "") for header in headers]
            self.worksheet.append_row(new_row)
        except APIError as e:
            st.error("Failed to append new item to the sheet.")
            st.exception(e)


# -----------------------------
# UI helpers
# -----------------------------
def get_icon(page_name, mapping):
    for key, icon in mapping.items():
        if key.lower() == page_name.lower():
            return icon
    return "tools"


def _count_by_category(records):
    # total_count, used_count for each category
    stats = {}
    for r in records:
        cat = str(r.get("category", "")).strip()
        if not cat:
            continue
        used = str(r.get("used", "")).strip().lower() in ["yes", "true", "1"]
        if cat not in stats:
            stats[cat] = {"total": 0, "used": 0}
        stats[cat]["total"] += 1
        if used:
            stats[cat]["used"] += 1
    return stats


def _metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _module_card(title, description):
    st.markdown(
        f"""
        <div class="module-card">
            <div class="module-title">{title}</div>
            <div class="module-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Pages
# -----------------------------
def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.write(f"Browse tools for {target_category}.")
    st.divider()

    try:
        tools = reader.get_filtered_tools(target_category=target_category)
    except APIError as e:
        st.error("Failed to fetch tools from Google Sheet.")
        st.exception(e)
        return

    search_query = st.text_input("Search by name", placeholder="Type a website or app name...").strip()
    filtered_tools = (
        [t for t in tools if search_query.lower() in str(t.get("name", "")).lower()]
        if search_query
        else tools
    )

    st.caption(f"Results: {len(filtered_tools)}")

    if filtered_tools:
        columns = st.columns([1, 1, 1])
        for idx, tool in enumerate(filtered_tools):
            col = columns[idx % 3]
            with col:
                st.markdown(
                    f"""
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
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No tools match your search.")


def render_add_item_page(reader):
    st.title("Add New Item")
    st.write("Fill the fields and submit.")
    st.divider()

    records = reader.get_all_records()
    categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip())) or [
        "Default"
    ]

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
                "used": used,
            }
            try:
                reader.append_new_item(new_item)
                st.success("New item added.")
            except Exception as e:
                st.error("Failed to add item.")
                st.exception(e)
        else:
            st.warning("Category and Name are required.")


def render_chatgpt_prompts_page(prompts_reader):
    st.title("ChatGPT Prompts")
    st.write("Short descriptions and ready prompts.")
    st.divider()

    try:
        records = prompts_reader.get_all_records()
    except APIError as e:
        st.error("Failed to load prompts.")
        st.exception(e)
        return

    if records:
        for row in records:
            st.write("• " + row.get("description", ""))
            st.code(row.get("prompt", ""))
            st.divider()
    else:
        st.info("No prompts found.")


def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.write("Describe and paste the prompt.")
    st.divider()

    description = st.text_area("Description")
    prompt = st.text_area("Prompt")

    if st.button("Add Prompt"):
        if description and prompt:
            new_prompt = {"description": description, "prompt": prompt}
            try:
                prompts_reader.append_new_item(new_prompt)
                st.success("Prompt added.")
            except Exception as e:
                st.error("Failed to add prompt.")
                st.exception(e)
        else:
            st.warning("Both fields are required.")


def home_page(records, categories, desc_map):
    st.markdown(
        """
        <div class="home-header">
            <h1 class="home-title">UpBizz Management Dashboard</h1>
            <p class="home-subtitle">Manage projects, people, credentials, designs, subscriptions, and weekly tasks, synced with Google Sheets.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    refreshed = datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y %H:%M")
    st.caption(f"Refreshed · {refreshed}")

    # Metrics
    stats = _count_by_category(records)
    metric_items = []
    for cat in categories:
        stat = stats.get(cat, {"used": 0, "total": 0})
        metric_items.append((cat, stat["used"]))

    if metric_items:
        cols_per_row = 4
        rows = (len(metric_items) + cols_per_row - 1) // cols_per_row
        for r in range(rows):
            cols = st.columns(cols_per_row)
            for i in range(cols_per_row):
                idx = r * cols_per_row + i
                if idx >= len(metric_items):
                    break
                with cols[i]:
                    label, value = metric_items[idx]
                    _metric_card(label, value)

    st.divider()

    # Modules at a Glance
    st.subheader("Modules At a Glance")
    cols_per_row = 3
    rows = (len(categories) + cols_per_row - 1) // cols_per_row
    for r in range(rows):
        cols = st.columns(cols_per_row)
        for i in range(cols_per_row):
            idx = r * cols_per_row + i
            if idx >= len(categories):
                break
            cat = categories[idx]
            with cols[i]:
                _module_card(cat, desc_map.get(cat, "Browse saved links and tools."))


# -----------------------------
# Main
# -----------------------------
def main():
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    try:
        creds_local = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    except Exception as e:
        st.error("Failed to load credentials from secrets.")
        st.exception(e)
        st.stop()

    main_reader = CollectifySheetReader(creds=creds_local)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds_local)

    try:
        records = main_reader.get_all_records()
        categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip()))
    except Exception as e:
        st.error("Failed to load categories.")
        st.exception(e)
        categories = []

    module_descriptions = {
        "Artificial Intelligence": "AI tools, models, and prompt libraries.",
        "Chrome Extensions": "Browser add-ons for daily work.",
        "Django": "Back-end packages and helpers.",
        "Free API Resources": "Open APIs for demos and apps.",
        "FrontEnd Tools": "UI kits, generators, and checkers.",
        "Icons Website": "Icon sets and SVG libraries.",
        "Programming Tools": "CLIs, debuggers, utilities.",
        "Python": "Libraries, docs, and snippets.",
        "React": "Components, templates, and guides.",
        "Useful Websites": "Helpful sites for work.",
        "VSCode Extensions": "Editor add-ons that save time.",
        "Web Design": "Inspiration, colors, and grids.",
        "Web Scraping": "Scrapers, proxies, and parsers.",
        "Youtube Videos": "Playlists and tutorials.",
    }

    page_modules = {
        "Home": lambda: home_page(records, categories, module_descriptions),
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds_local),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
    }

    for category in categories:
        page_modules[category] = lambda category=category: render_category_page(main_reader, category)

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
        "Youtube Videos": "youtube",
    }

    menu_keys_top = ["Home", "Add New Item", "Add New ChatGPT Prompt", "Todo App", "---", "ChatGPT Prompts"]
    menu_keys_bottom = categories
    menu_keys = menu_keys_top + menu_keys_bottom
    menu_icons = [get_icon(key, icon_mapping) for key in menu_keys]

    with st.sidebar:
        selected = option_menu("Useful Tools", menu_keys, icons=menu_icons, default_index=0)

    if selected != "---":
        page_modules[selected]()


if __name__ == "__main__":
    main()
