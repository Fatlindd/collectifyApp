import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from datetime import datetime
from style import STYLE_CSS  # Custom CSS file
from todo import main as todo_main  # Todo module

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")

# Inject your existing custom styles
st.markdown(STYLE_CSS, unsafe_allow_html=True)

# Additional dashboard CSS (cards, grids, spacing)
DASHBOARD_CSS = """
<style>
/* Header */
.dashboard-header h1 {
  font-size: 44px; line-height: 1.1; margin-bottom: 8px;
}
.dashboard-header p.subtitle {
  color: rgba(255,255,255,0.75); margin: 0 0 6px 0; font-size: 15px;
}
.dashboard-header .refreshed {
  font-size: 12px; color: rgba(255,255,255,0.55);
}

/* KPIs */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin: 22px 0 26px 0;
}
.kpi-card {
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 18px 18px 14px 18px;
}
.kpi-card .label {
  font-size: 13px; color: rgba(255,255,255,0.70); margin-bottom: 6px;
}
.kpi-card .value {
  font-size: 40px; font-weight: 700; color: #ffffff;
}

/* Section title */
.section-title {
  font-weight: 700; font-size: 16px; letter-spacing: .02em; margin: 6px 0 12px 0;
  color: rgba(255,255,255,0.85);
}

/* Module grid */
.module-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.module-card {
  background: #0b1220;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 18px;
}
.module-card .title {
  display:flex; align-items:center; gap:10px;
  font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 8px;
}
.module-card .desc {
  color: rgba(255,255,255,0.72); font-size: 14px; line-height: 1.5;
}
.module-emoji {
  font-size: 20px; width: 28px; height: 28px; display:flex; align-items:center; justify-content:center;
  background: rgba(255,255,255,0.06); border-radius: 8px;
}

/* Responsive tweaks */
@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .module-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 800px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .module-grid { grid-template-columns: 1fr; }
}
</style>
"""
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

# ---------------------------
# Credentials
# ---------------------------
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

    search_query = st.text_input(
        "Search by name",
        placeholder="Type a website/app name..."
    ).strip()

    if search_query:
        filtered_tools = [t for t in tools if search_query.lower() in str(t.get("name", "")).lower()]
    else:
        filtered_tools = tools

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


def render_add_item_page(reader):
    st.title("Add New Item")
    st.write("Use this page to contribute a new tool to the collection. Fill in the fields below.")
    st.divider()

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


# ---------------------------
# NEW: Dashboard-style Home
# ---------------------------
def home_page(main_reader, prompts_reader, categories):
    # Header
    st.markdown(
        f"""
        <div class="dashboard-header">
          <h1>UpBizz Management Dashboard</h1>
          <p class="subtitle">Manage projects, people, credentials, designs, subscriptions, and weekly tasks — all synced with Google Sheets.</p>
          <div class="refreshed">Refreshed · {datetime.now().strftime("%b %d, %Y %H:%M")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Compute KPIs from your data
    records = main_reader.get_all_records()
    total_tools = len(records)
    categories_count = len(set(r.get("category", "").strip() for r in records if r.get("category")))
    used_count = sum(1 for r in records if str(r.get("used", "")).strip().lower() == "yes")
    unused_count = max(total_tools - used_count, 0)

    try:
        prompts_count = len(prompts_reader.get_all_records())
    except Exception:
        prompts_count = 0

    # KPI row
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card"><div class="label">Total Tools</div><div class="value">{total_tools}</div></div>
          <div class="kpi-card"><div class="label">Categories</div><div class="value">{categories_count}</div></div>
          <div class="kpi-card"><div class="label">Used</div><div class="value">{used_count}</div></div>
          <div class="kpi-card"><div class="label">Unused</div><div class="value">{unused_count}</div></div>
          <div class="kpi-card"><div class="label">ChatGPT Prompts</div><div class="value">{prompts_count}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section: Modules at a Glance (static labels to mirror the screenshot vibe)
    st.markdown('<div class="section-title">MODULES AT A GLANCE</div>', unsafe_allow_html=True)

    modules = [
        {"emoji": "🧮", "title": "Project Costs",
         "desc": "Track budgets, expenses, company win, left budget, progress and dates. Daily Salary is auto-filled by Apps Script."},
        {"emoji": "👥", "title": "Employees",
         "desc": "Directory of roles, salaries and notes. Powers salary lookups used in project calculations."},
        {"emoji": "🎨", "title": "Figma Clients",
         "desc": "Clients’ design links, owners and statuses in a searchable, filterable table."},
        {"emoji": "🔐", "title": "Credentials",
         "desc": "Securely store platform logins and API keys in a structured sheet."},
        {"emoji": "🧭", "title": "UpBizz Landing Page",
         "desc": "Catalog of landing pages, who worked on them, and key links."},
        {"emoji": "📅", "title": "Tasks History (Weekly)",
         "desc": "Browse weekly task reports: stacked by person, status and project."},
    ]

    # Draw module cards
    cards_html = '<div class="module-grid">'
    for m in modules:
        cards_html += f"""
          <div class="module-card">
            <div class="title">
              <span class="module-emoji">{m['emoji']}</span>
              <span>{m['title']}</span>
            </div>
            <div class="desc">{m['desc']}</div>
          </div>
        """
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)


# ---------------------------
# App routing
# ---------------------------
def get_icon(page_name, mapping):
    for key, icon in mapping.items():
        if key.lower() == page_name.lower():
            return icon
    return "tools"


def main():
    st.markdown(STYLE_CSS, unsafe_allow_html=True)

    # Load credentials (again inside main to be safe in reruns)
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

    # Readers
    main_reader = CollectifySheetReader(creds=creds)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    # Categories for dynamic menu
    try:
        records = main_reader.get_all_records()
        categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip()))
    except Exception as e:
        st.error("⚠️ Failed to load categories.")
        st.exception(e)
        categories = []

    # Page registry
    page_modules = {
        "Home": lambda: home_page(main_reader, prompts_reader, categories),
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
    }
    for category in categories:
        page_modules[category] = lambda category=category: render_category_page(main_reader, category)

    # Icons
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
        selected = option_menu(
            "Useful Tools",
            menu_keys,
            icons=menu_icons,
            default_index=0
        )

    if selected != "---":
        page_modules[selected]()


if __name__ == "__main__":
    main()
