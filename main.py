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

# Bootstrap Icons (for sidebar + home cards)
st.markdown(
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">',
    unsafe_allow_html=True,
)

# ------------------------------
# Inline CSS (no body/html bg; add card gap; logo image styles)
# ------------------------------
STYLE_CSS = """
<style>
:root {
  --card-bg: #ffffff;
  --card-border: #eaeaea;
  --card-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* Simple cards used on Home */
.home-card{
  background:var(--card-bg);
  border:1px solid var(--card-border);
  border-radius:12px;
  padding:16px;
  box-shadow:var(--card-shadow);
  height:100%;
  margin-bottom:18px; /* gap between cards */
}
.home-card .title{
  display:flex; align-items:center; gap:.6rem;
  font-weight:700; font-size:18px;
}
.home-card .desc{ margin-top:6px; color:#4b5563; line-height:1.45; font-size:14px; }
.icon-badge{
  display:inline-flex; align-items:center; justify-content:center;
  width:34px; height:34px; border-radius:10px; background:#eef6ff; color:#0b6bcb; font-size:18px;
}

/* Tool cards inside category pages (navbar links) */
.tool-card{
  background:#fff; border:1px solid var(--card-border); border-radius:12px;
  box-shadow:var(--card-shadow); padding:14px; height:100%; margin-bottom:18px; /* gap between cards */
}
.tool-head{ display:flex; align-items:center; gap:10px; }
.tool-logo{
  width:48px; height:48px; border-radius:10px; border:1px solid #f0f0f0;
  background:#fafafa; object-fit:contain; display:block;
}
.tool-title{ font-weight:700; font-size:16px; }
.tool-desc{ color:#4b5563; font-size:14px; margin-top:6px; min-height:40px; }
.tool-actions{ margin-top:10px; }
.tool-button{
  background:#0ea5e9; color:#fff; border:none; border-radius:10px;
  padding:8px 12px; font-weight:600; cursor:pointer;
}
.tool-button:hover{ filter:brightness(.95); }
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
                "name":"name","description":"description","logo_url":"logo_url",
                "store_link":"store_link","button_name":"button_name"
            }
        data = self.get_all_records()
        filtered = [
            {out: row.get(src,"") for out,src in output_mapping.items()}
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
# Category Page (uses logo_url images + better spacing)
# ------------------------------
def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.divider()

    try:
        tools = reader.get_filtered_tools(target_category=target_category)
    except APIError as e:
        st.error("❌ Failed to fetch tools from Google Sheet.")
        st.exception(e)
        return

    query = st.text_input("Search by name", placeholder="Type a website/app name...").strip()
    filtered = [t for t in tools if query.lower() in str(t.get("name","")).lower()] if query else tools

    st.caption(f"Results: {len(filtered)}")

    if not filtered:
        st.info("ℹ️ No tools match your search.")
        return

    cols = st.columns(3)  # responsive: Streamlit stacks these on small screens
    for i, tool in enumerate(filtered):
        with cols[i % 3]:
            name = tool.get("name", "Untitled Tool")
            desc = tool.get("description", "No description available.")
            logo = tool.get("logo_url", "")
            link = tool.get("store_link", "#")
            btn  = tool.get("button_name", "Open")

            st.markdown(
                f"""
                <div class="tool-card">
                  <div class="tool-head">
                    <img class="tool-logo" src="{logo}" alt="{name} logo"/>
                    <div class="tool-title">{name}</div>
                  </div>
                  <div class="tool-desc">{desc}</div>
                  <div class="tool-actions">
                    <a href="{link}" target="_blank"><button class="tool-button">{btn}</button></a>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ------------------------------
# Add Item Page (unchanged)
# ------------------------------
def render_add_item_page(reader):
    st.title("Add New Item")
    st.divider()

    records = reader.get_all_records()
    categories = sorted({r.get("category","").strip() for r in records if r.get("category","").strip()}) or ["Default"]

    col1, col2 = st.columns(2)
    with col1: category = st.selectbox("Select Category", options=categories)
    with col2: name = st.text_input("Name")

    description = st.text_area("Description")

    col3, col4 = st.columns(2)
    with col3: logo_url  = st.text_input("Logo URL")
    with col4: store_link = st.text_input("Store Link")

    col5, col6 = st.columns(2)
    with col5: button_name = st.text_input("Button Name")
    with col6: used = st.selectbox("Used", options=["Yes","No"])

    if st.button("Add Item"):
        if name and category:
            try:
                reader.append_new_item({
                    "category":category, "name":name, "description":description,
                    "logo_url":logo_url, "store_link":store_link,
                    "button_name":button_name, "used":used
                })
                st.success("✅ New item added successfully!")
            except Exception as e:
                st.error("❌ Failed to add item.")
                st.exception(e)
        else:
            st.warning("⚠️ Please fill in at least the Category and Name fields.")

# ------------------------------
# Prompts Pages (kept as st.code())
# ------------------------------
def render_chatgpt_prompts_page(prompts_reader):
    st.title("ChatGPT Prompts")
    st.write("Browse useful ChatGPT prompts with short descriptions and pre-filled content.")
    st.divider()
    try:
        records = prompts_reader.get_all_records()
    except APIError as e:
        st.error("❌ Failed to load prompts.")
        st.exception(e); return
    if not records:
        st.info("ℹ️ No prompts found."); return
    for row in records:
        st.write("📌 " + row.get("description",""))
        st.code(row.get("prompt",""), language=None)
        st.divider()

def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.divider()
    description = st.text_area("Description")
    prompt = st.text_area("Prompt")
    if st.button("Add Prompt"):
        if description and prompt:
            try:
                prompts_reader.append_new_item({"description":description,"prompt":prompt})
                st.success("✅ Prompt added successfully!")
            except Exception as e:
                st.error("❌ Failed to add prompt."); st.exception(e)
        else:
            st.warning("⚠️ Please fill in both the Description and Prompt fields.")

# ------------------------------
# Sidebar Icons
# ------------------------------
ICON_MAP = {
    "Home":"house", "Add New Item":"plus-square", "Add New ChatGPT Prompt":"plus-circle",
    "---":"dash", "Todo App":"list-task", "ChatGPT Prompts":"chat-dots",
    "Artificial Intelligence":"robot", "Chrome Extensions":"puzzle", "Django":"server",
    "Free API Resources":"cloud", "FrontEnd Tools":"palette", "Icons Website":"image",
    "Programming Tools":"gear", "Python":"terminal", "React":"code-slash",
    "Useful Website":"link-45deg", "Useful Websites":"link-45deg",
    "Vscode Extensions":"plug", "Web Design":"brush", "Web Scraping":"search",
    "Youtube Videos":"youtube",
}
def get_icon(name): return ICON_MAP.get(name, "tools")

# ------------------------------
# Home (unchanged look; cards are compact; no bg override)
# ------------------------------
def home_page(nav_items_for_cards):
    st.title("Welcome to Collectify Tools")
    st.divider()
    st.subheader("Modules at a Glance")

    items = [i for i in nav_items_for_cards if i not in ("Home","---")]
    cols = st.columns(3)
    for idx, title in enumerate(items):
        with cols[idx % 3]:
            desc_map = {
                "ChatGPT Prompts":"Save & reuse high-impact prompts.",
                "Artificial Intelligence":"AI tools and workflows.",
                "Chrome Extensions":"Boost your browser productivity.",
                "Django":"Admin helpers & packages.",
                "Free API Resources":"Public APIs for prototypes.",
                "FrontEnd Tools":"UI kits & inspectors.",
                "Icons Website":"Icon packs & search.",
                "Programming Tools":"CLIs, linters, formatters.",
                "Python":"Libraries & utilities.",
                "React":"Components & hooks.",
                "Useful Website":"Handy links & utilities.",
                "Useful Websites":"Handy links & utilities.",
                "Vscode Extensions":"Editor add-ons that help.",
                "Web Design":"Layouts & inspiration.",
                "Web Scraping":"Scrapers, parsers, proxies.",
                "Youtube Videos":"Learning and breakdowns.",
                "Add New Item":"Create a new tool entry.",
                "Add New ChatGPT Prompt":"Capture a new prompt.",
                "Todo App":"Plan and track tasks.",
            }
            st.markdown(
                f"""
                <div class="home-card">
                  <div class="title">
                    <span class="icon-badge"><i class="bi bi-{get_icon(title)}"></i></span>
                    <span>{title}</span>
                  </div>
                  <div class="desc">{desc_map.get(title, f"Open {title} from the sidebar.")}</div>
                </div>
                """, unsafe_allow_html=True
            )

# ------------------------------
# Main
# ------------------------------
def main():
    main_reader = CollectifySheetReader(creds=creds)
    prompts_reader = CollectifySheetReader(worksheet_name="ChatGPT Prompts", creds=creds)

    try:
        records = main_reader.get_all_records()
        categories = sorted({r.get("category","").strip() for r in records if r.get("category","").strip()})
    except Exception as e:
        st.error("⚠️ Failed to load categories."); st.exception(e); categories = []

    page_modules = {
        "Home": lambda: home_page(nav_items_for_cards=[]),
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader),
    }
    for c in categories:
        page_modules[c] = (lambda _c=c: render_category_page(main_reader, _c))

    menu_keys_top = ["Home","Add New Item","Add New ChatGPT Prompt","Todo App","---","ChatGPT Prompts"]
    menu_keys_bottom = categories
    menu_keys = menu_keys_top + menu_keys_bottom
    menu_icons = [get_icon(k) for k in menu_keys]

    with st.sidebar:
        selected = option_menu("Useful Tools", menu_keys, icons=menu_icons, default_index=0)

    page_modules["Home"] = lambda: home_page(menu_keys)

    if "__force_nav__" in st.session_state:
        selected = st.session_state.pop("__force_nav__")

    if selected != "---":
        if selected not in page_modules and selected in categories:
            render_category_page(main_reader, selected)
        else:
            page_modules.get(selected, lambda: st.error("Page not found"))()

if __name__ == "__main__":
    main()
