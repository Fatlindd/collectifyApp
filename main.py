import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from style import STYLE_CSS  # Custom CSS file
from todo import main as todo_main  # Todo module
import hashlib

# Set page configuration
st.set_page_config(page_title="Useful Tools", page_icon=":zap:", layout="wide")

# Inject custom styles (global) + local card CSS
CARD_CSS = """
<style>
.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}
@media (max-width: 1100px) {
  .tool-grid { grid-template-columns: 1fr; }
}

.tool-card {
  position: relative;
  border-radius: 18px;
  border: 1px solid #E8E8EE;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0.00));
  box-shadow: 0 1px 0 rgba(0,0,0,0.02);
}

.tool-card::before {
  /* left accent stripe */
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 8px;
  background: var(--accent, #21c7b9);
}

.tool-card__inner {
  padding: 20px 22px 18px 22px;
}

.tool-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.tool-card__title {
  font-size: 28px;
  font-weight: 700;
  color: #2B2B36;
  line-height: 1.2;
}

.badge {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: #114a1f;
  background: #DFF7E7; /* Active green */
  border: 1px solid #CBEFDB;
  white-space: nowrap;
}
.badge.inactive {
  color: #4a4a50;
  background: #F0F0F3;
  border-color: #E5E5EA;
}

.tool-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
  margin-top: 8px;
}

.meta-block { display: flex; flex-direction: column; gap: 6px; }
.meta-label { color: #6F7081; font-size: 13px; }
.meta-value { color: #1f1f29; font-size: 18px; font-weight: 700; }

.pill {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: #E8EEFF;
  color: #2D3B88;
  font-weight: 600;
  font-size: 13px;
  border: 1px solid #DBE2FD;
}

.tool-card__footer {
  border-top: 1px solid #EFF0F4;
  margin-top: 16px;
  padding-top: 14px;
  color: #30303B;
  font-size: 14px;
}

.tool-card a.card-link {
  display: inline-block;
  margin-top: 6px;
  text-decoration: none;
  border-bottom: 1px dashed #21c7b9;
  color: #148f87;
  font-weight: 600;
}

.tool-card .price {
  font-size: 20px;
  font-weight: 800;
}
</style>
"""

st.markdown(STYLE_CSS, unsafe_allow_html=True)
st.markdown(CARD_CSS, unsafe_allow_html=True)

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
        # Add richer fields to support the card UI
        if output_mapping is None:
            output_mapping = {
                "name": "name",
                "description": "description",     # optional (notes/body)
                "logo_url": "logo_url",           # optional (not shown in this design)
                "store_link": "store_link",       # fallback link
                "button_name": "button_name",     # optional (not shown in this design)
                "status": "status",               # Active/Inactive
                "category": "category",           # Category label
                "plan_tier": "plan_tier",         # e.g., €17.00
                "team": "team",                   # e.g., Developer
                "seats": "seats",                 # integer/string
                "total_expense": "total_expense", # e.g., €51.00
                "notes": "notes",                 # longer description
                "link_url": "link_url"            # preferred link for "Learn more"
            }
        data = self.get_all_records()
        filtered = []
        for row in data:
            if row.get(category_field) == target_category:
                mapped = {out: row.get(src, "") for out, src in output_mapping.items()}
                # Backwards-compatible fallbacks
                if not mapped.get("notes") and mapped.get("description"):
                    mapped["notes"] = mapped["description"]
                if not mapped.get("link_url") and mapped.get("store_link"):
                    mapped["link_url"] = mapped["store_link"]
                filtered.append(mapped)
        return filtered

    def append_new_item(self, item):
        try:
            headers = self.worksheet.row_values(1)
            new_row = [item.get(header, "") for header in headers]
            self.worksheet.append_row(new_row)
        except APIError as e:
            st.error("❌ Failed to append new item to the sheet.")
            st.exception(e)


# ---------- Helpers for card rendering ----------
def _accent_from_text(text: str) -> str:
    """Generate a stable accent color from a text (category/name)."""
    if not text:
        return "#21c7b9"
    h = hashlib.md5(text.encode()).hexdigest()
    # pick a pleasant hue from hash, keep saturation/lightness fixed (HSL -> rough map to hex)
    hue = int(h[:2], 16) % 360
    # Simple HSL to hex approximation with fixed S/L
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hue/360.0, 0.90, 0.45)  # light, soft
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def _fmt(value, default="—"):
    return str(value).strip() if str(value).strip() else default

def _badge(status: str) -> str:
    s = (status or "").strip().lower()
    cls = "badge" if s == "active" else "badge inactive"
    label = "Active" if s == "active" else (status or "—")
    return f'<span class="{cls}">{label}</span>'

def _pill(text: str) -> str:
    return f'<span class="pill">{_fmt(text, "—")}</span>'

def _price(text: str) -> str:
    t = _fmt(text, "—")
    if t != "—":
        return f'<span class="price">{t}</span>'
    return t

def render_tool_card(tool: dict):
    title = _fmt(tool.get("name"))
    status_html = _badge(tool.get("status", "Active"))
    category = _fmt(tool.get("category"))
    plan_tier = _price(tool.get("plan_tier"))
    team = _pill(tool.get("team"))
    seats = _fmt(tool.get("seats"))
    total_expense = _price(tool.get("total_expense"))
    notes = _fmt(tool.get("notes"), "")
    link_url = tool.get("link_url") or "#"

    accent = _accent_from_text(category or title)

    return f"""
    <div class="tool-card" style="--accent: {accent};">
      <div class="tool-card__inner">
        <div class="tool-card__header">
          <div class="tool-card__title">{title}</div>
          {status_html}
        </div>

        <div class="tool-card__meta">
          <div class="meta-block">
            <div class="meta-label">Category</div>
            <div class="meta-value">{category}</div>
          </div>

          <div class="meta-block">
            <div class="meta-label">Plan/Tier</div>
            <div class="meta-value">{plan_tier}</div>
          </div>

          <div class="meta-block">
            <div class="meta-label">Team</div>
            <div class="meta-value">{team}</div>
          </div>

          <div class="meta-block">
            <div class="meta-label">Seats</div>
            <div class="meta-value">{seats}</div>
          </div>

          <div class="meta-block">
            <div class="meta-label">Total Expense</div>
            <div class="meta-value">{total_expense}</div>
          </div>
        </div>

        <div class="tool-card__footer">
          {notes}
          {"<br/>" if notes != "—" else ""}
          <a class="card-link" href="{link_url}" target="_blank" rel="noopener">Learn more</a>
        </div>
      </div>
    </div>
    """


# ---------- Pages ----------
def render_category_page(reader, target_category):
    st.title(f"{target_category} Tools")
    st.write(
        f"This page displays a curated list of {target_category} tools and resources."
    )
    st.divider()

    try:
        tools = reader.get_filtered_tools(target_category=target_category)
    except APIError as e:
        st.error("❌ Failed to fetch tools from Google Sheet.")
        st.exception(e)
        return

    # 🔎 Search by name (case-insensitive)
    search_query = st.text_input(
        "Search by name",
        placeholder="Type a website/app name..."
    ).strip()

    if search_query:
        filtered_tools = [t for t in tools if search_query.lower() in str(t.get("name", "")).lower()]
    else:
        filtered_tools = tools

    st.caption(f"Results: {len(filtered_tools)}")

    if not filtered_tools:
        st.info("ℹ️ No tools match your search.")
        return

    # Render as a responsive grid of cards
    st.markdown('<div class="tool-grid">', unsafe_allow_html=True)
    for tool in filtered_tools:
        st.markdown(render_tool_card(tool), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


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


def home_page():
    st.title("Welcome to Collectify Tools")
    st.write(
        "Discover a curated list of tools, websites, and AI resources. Use the sidebar to explore categories, add your own, or check out ChatGPT prompts."
    )
    st.divider()
    st.markdown(
        """
        ### 🚀 About This App

        I built this platform to centralize the tools and prompts that make my development journey smoother and more productive.

        **New! Todo App:** Seamlessly add, update, and delete tasks to stay organized and boost your productivity—all in one place.
        """
    )


def get_icon(page_name, mapping):
    for key, icon in mapping.items():
        if key.lower() == page_name.lower():
            return icon
    return "tools"


def main():
    # Reinforce styles in case Streamlit reruns
    st.markdown(STYLE_CSS, unsafe_allow_html=True)
    st.markdown(CARD_CSS, unsafe_allow_html=True)

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

    # Sidebar dynamic categories
    try:
        records = main_reader.get_all_records()
        categories = sorted(set(r.get("category", "").strip() for r in records if r.get("category", "").strip()))
    except Exception as e:
        st.error("⚠️ Failed to load categories.")
        st.exception(e)
        categories = []

    page_modules = {
        "Home": home_page,
        "Add New Item": lambda: render_add_item_page(main_reader),
        "Add New ChatGPT Prompt": lambda: render_add_chatgpt_prompt_page(prompts_reader),
        "Todo App": lambda: todo_main(creds),
        "---": lambda: None,
        "ChatGPT Prompts": lambda: render_chatgpt_prompts_page(prompts_reader)
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
        "Youtube Videos": "youtube"
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
