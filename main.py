import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from todo import main as todo_main  # Todo module

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(page_title="Collectify Apps", page_icon=":zap:", layout="wide")

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
# Subtitles for each category/page
# ------------------------------
SUBTITLE_MAP = {
    "Artificial Intelligence": "Find the right AI tool for building, automating, and creating smarter solutions.",
    "Chrome Extensions": "Explore the best Chrome extensions to optimize security, creativity, and daily use.",
    "Django": "Discover powerful Django libraries for cleaner code, better performance, and faster delivery.",
    "Free API Resources": "Your go-to directory of free APIs to experiment, learn, and build smarter apps.",
    "FrontEnd Tools": "A collection of frontend resources to design, style, and optimize modern websites.",
    "Icons Website": "Boost your design workflow with flexible, high-quality icon resources.",
    "Programming Tools": "Essential editors, IDEs, and platforms to write, test, and debug code efficiently.",
    "Python": "Practical Python packages to make coding easier, faster, and more secure.",
    "React": "From UI kits to code converters—everything you need for faster React workflows.",
    "Useful Website": "Explore practical websites that save time and help you work smarter.",
    "Useful Websites": "Explore practical websites that save time and help you work smarter.",
    "Vscode Extensions": "Enhance your Visual Studio Code editor with tools that save time and reduce errors.",
    "Web Design": "Discover tools that simplify web design, from color palettes to UI components.",
    "Web Scraping": "A curated collection of tools and resources for data extraction, proxies, and automation.",
    "Youtube Videos": "Video resources to help you code smarter, faster, and more effectively.",
    "ChatGPT Prompts": "Browse useful ChatGPT prompts with short descriptions and pre-filled content.",
}

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

    # Subtitle (if configured)
    if target_category in SUBTITLE_MAP:
        st.write(SUBTITLE_MAP[target_category])

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
    st.write("Fill out the form below to add a new tool into the Collectify Apps library.")
    st.divider()

    with st.form("add_item_form", clear_on_submit=True):
        st.subheader("Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox(
                "Select Category",
                options=sorted({r.get("category", "").strip() for r in reader.get_all_records() if r.get("category", "").strip()}) or ["Default"],
                help="Choose the most relevant category for this tool."
            )
        with col2:
            name = st.text_input("Tool Name", placeholder="e.g. Postman, TailwindCSS")

        description = st.text_area("Description", placeholder="Write a short summary of what this tool does.")

        col3, col4 = st.columns(2)
        with col3:
            logo_url = st.text_input("Logo URL", placeholder="Paste an image link here")
        with col4:
            store_link = st.text_input("Website / Store Link", placeholder="https://...")

        col5, col6 = st.columns(2)
        with col5:
            button_name = st.text_input("Button Label", placeholder="Open, Visit, Try Now")
        with col6:
            used = st.selectbox("Mark as Used", options=["Yes", "No"])

        submitted = st.form_submit_button("Add Item")
        if submitted:
            if name and category:
                try:
                    reader.append_new_item({
                        "category": category,
                        "name": name,
                        "description": description,
                        "logo_url": logo_url,
                        "store_link": store_link,
                        "button_name": button_name,
                        "used": used,
                    })
                    st.success(f"'{name}' added successfully to {category}!")
                except Exception as e:
                    st.error("Failed to add item.")
                    st.exception(e)
            else:
                st.warning("Please provide at least the **Category** and **Name**.")

# ------------------------------
# Prompts Pages (now use SUBTITLE_MAP)
# ------------------------------
def render_chatgpt_prompts_page(prompts_reader):
    st.title("ChatGPT Prompts")
    st.write(SUBTITLE_MAP.get("ChatGPT Prompts", "Browse useful ChatGPT prompts."))
    st.divider()
    try:
        records = prompts_reader.get_all_records()
    except APIError as e:
        st.error("Failed to load prompts.")
        st.exception(e); return
    if not records:
        st.info("No prompts found."); return
    for row in records:
        st.write("" + row.get("description",""))
        st.code(row.get("prompt",""), language=None)
        st.divider()

def render_add_chatgpt_prompt_page(prompts_reader):
    st.title("Add New ChatGPT Prompt")
    st.write("Store useful prompts with descriptions so they can be easily reused later.")
    st.divider()

    with st.form("add_prompt_form", clear_on_submit=True):
        description = st.text_area("Description", placeholder="e.g. Summarize long articles into bullet points")
        prompt = st.text_area("Prompt", placeholder="Paste or write the full ChatGPT prompt here")

        submitted = st.form_submit_button("Save Prompt")
        if submitted:
            if description and prompt:
                try:
                    prompts_reader.append_new_item({"description": description, "prompt": prompt})
                    st.success("🎉 Prompt added successfully!")
                except Exception as e:
                    st.error("❌ Failed to add prompt.")
                    st.exception(e)
            else:
                st.warning("⚠️ Please fill in both the **Description** and **Prompt**.")


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
# ------------------------------
# Home (richer blurbs for "Explore All Categories")
# ------------------------------
def home_page(nav_items_for_cards):
    st.title("Welcome to Collectify Apps")
    st.write(
    "This app was created by **Fatlindi** as a personal productivity companion. "
    "It organizes collectify apps into categories for faster access and daily learning. "
    "The app is also connected to a Telegram bot, which sends me a random tool each day "
    "along with its category and purpose—helping me discover and apply new resources consistently."
    )

    st.divider()
    st.subheader("Explore All Categories")

    items = [i for i in nav_items_for_cards if i not in ("Home","---")]

    # Rephrased, more descriptive explanations for each module
    desc_map = {
        "ChatGPT Prompts": "A library of ready-to-use prompts with short notes. Copy, tweak, and paste to speed up ideation, coding help, and writing tasks.",
        "Artificial Intelligence": "Curated AI platforms for building, automating, and accelerating work—use them for prototyping apps, content generation, and task automation.",
        "Chrome Extensions": "Handpicked browser add-ons that improve productivity, security, and creativity directly in Chrome while you browse or build.",
        "Django": "Practical Django packages and utilities to ship features faster—forms, static files, admin helpers, and performance tools.",
        "Free API Resources": "A directory of free/public APIs to experiment with datasets, validate ideas, and integrate services without upfront costs.",
        "FrontEnd Tools": "Design and UI helpers—CSS/SVG generators, loaders, templates, and inspectors—to craft polished, responsive interfaces quicker.",
        "Icons Website": "Icon libraries and icon-building tools to keep your UI consistent, scalable, and on-brand without reinventing assets.",
        "Programming Tools": "Editors, IDEs, and general dev utilities for writing, testing, debugging, and collaborating across languages.",
        "Python": "Focused Python utilities (env, parsing, config) that make scripting, automation, and app configuration simpler and safer.",
        "React": "UI kits, templates, and helper utilities that speed up component design, JSX conversion, and app scaffolding in React.",
        "Useful Website": "A mixed toolkit of online services—learning, utilities, and references—that save time in day-to-day work.",
        "Useful Websites": "A mixed toolkit of online services—learning, utilities, and references—that save time in day-to-day work.",
        "Vscode Extensions": "VS Code add-ons that reduce errors, automate formatting, visualize data, and personalize your editor for faster development.",
        "Web Design": "Resources for inspiration and execution—color tools, layout systems, UI kits, and collaboration tools for design workflows.",
        "Web Scraping": "Utilities for extraction and automation—proxy lists, UA helpers, validators, and scripts to collect and debug web data responsibly.",
        "Youtube Videos": "Curated video tutorials (Python, React, Django, full-stack) to learn by building real projects step by step.",
        "Add New Item": "Create a new catalog entry: define the category, name, logo, link, and description to expand the library.",
        "Add New ChatGPT Prompt": "Store a new prompt with a short description so your team can quickly find and reuse it later.",
        "Todo App": "Lightweight task tracker to plan work, record progress, and keep personal or team tasks visible inside the dashboard.",
    }

    cols = st.columns(3)
    for idx, title in enumerate(items):
        with cols[idx % 3]:
            st.markdown(
                f"""
                <div class="home-card">
                  <div class="title">
                    <span class="icon-badge"><i class="bi bi-{get_icon(title)}"></i></span>
                    <span>{title}</span>
                  </div>
                  <div class="desc">{desc_map.get(title, f"Open {title} from the sidebar to explore tools and resources.")}</div>
                </div>
                """,
                unsafe_allow_html=True
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
        selected = option_menu("Collectify Apps", menu_keys, icons=menu_icons, default_index=0)

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
