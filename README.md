# 📦 CollectifyApp

CollectifyApp is a modern, Streamlit-powered productivity suite that integrates a categorized tool directory, ChatGPT prompt collection, and a fully interactive Todo app. It is designed to help developers, learners, and tech enthusiasts stay organized, explore useful tools, and streamline their workflow—all from a single UI.

---

## 🔍 Features

### 🧰 Tool Collection
- Curated cards with icons, links, and descriptions.
- Filter by categories like "AI Tools", "Chrome Extensions", "Frontend Tools", and more.
- Easily add new tools directly to a connected Google Sheet.

### 💡 ChatGPT Prompt Vault
- Browse and use high-quality ChatGPT prompts for daily productivity.
- Add new prompt ideas via a simple form.

### ✅ Todo Management App
- Add, read, update, and delete tasks in real-time.
- Google Sheets-based storage for persistent and collaborative todo lists.
- Custom priority and status indicators with color styling.

---

## 🛠 Tech Stack

- **Frontend & App Framework:** [Streamlit](https://streamlit.io/)
- **Backend Integration:** Google Sheets API via `gspread`
- **Authentication:** Google Service Account (via `st.secrets`)
- **UI Components:** `streamlit-option-menu`, HTML/CSS customization
- **Data Handling:** `pandas`, `datetime`

---

## 📁 Project Structure

