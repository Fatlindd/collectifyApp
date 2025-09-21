import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from gspread.exceptions import APIError
from google.oauth2 import service_account
import pandas as pd
import datetime

# ----------------------------------------
# Utility: style the status column
# ----------------------------------------
def color_status(val):
    if val == "Completed":
        return "background-color: #77B254; color: white;"
    elif val == "Incomplete":
        return "background-color: #FF7777; color: white;"
    elif val == "In Progress":
        return "background-color: #4CC9FE; color: white;"
    else:
        return ""

# ----------------------------------------
# Google Sheets client handler
# ----------------------------------------
class GoogleSheetClient:
    def __init__(self, creds, spreadsheet_name="Collectify", worksheet_name="Todo"):
        self.client = gspread.authorize(creds)
        try:
            self.sheet = self.client.open(spreadsheet_name).worksheet(worksheet_name)
        except APIError as e:
            st.error("🚫 Could not access the 'Todo' worksheet in the 'Collectify' spreadsheet.")
            st.exception(e)
            st.stop()

    def read_all_values(self):
        try:
            return self.sheet.get_all_values()
        except APIError as e:
            st.error("❌ Failed to read data from Google Sheets.")
            st.exception(e)
            return []

    def add_todo(self, todo_item, priority):
        try:
            date_added = datetime.datetime.now().strftime('%d/%m/%Y')
            self.sheet.append_row([todo_item, priority, date_added, "", "Incomplete"])
        except APIError as e:
            st.error("❌ Failed to add new todo.")
            st.exception(e)

    def update_todo(self, row_index, todo_item, priority, date_completed, status):
        try:
            date_added = self.sheet.cell(row_index, 3).value
            formatted_date_completed = date_completed.strftime('%d/%m/%Y') if hasattr(date_completed, 'strftime') else date_completed
            self.sheet.update(f"A{row_index}:E{row_index}", [[todo_item, priority, date_added, formatted_date_completed, status]])
        except APIError as e:
            st.error("⚠️ Failed to update the todo item.")
            st.exception(e)

    def delete_todo(self, row_index):
        try:
            self.sheet.delete_rows(row_index)
        except APIError as e:
            st.error("❌ Failed to delete the todo.")
            st.exception(e)

# ----------------------------------------
# Todo app logic wrapper
# ----------------------------------------
class TodoApp:
    def __init__(self, sheet_client):
        self.sheet_client = sheet_client

    def list_todos(self):
        data = self.sheet_client.read_all_values()
        if len(data) > 1:
            headers = data[0]
            todos = data[1:]
            return headers, todos
        return [], []

    def create_todo(self, todo_item, priority):
        self.sheet_client.add_todo(todo_item, priority)

    def modify_todo(self, row_index, todo_item, priority, date_completed, status):
        self.sheet_client.update_todo(row_index, todo_item, priority, date_completed, status)

    def remove_todo(self, row_index):
        self.sheet_client.delete_todo(row_index)

# ----------------------------------------
# Helpers for DataFrame, metrics & search
# ----------------------------------------
def build_df(headers, rows):
    df = pd.DataFrame(rows, columns=headers)
    # Normalizim headers -> lower/strip për adresim të sigurt
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def compute_stats(df):
    # Përdor casefold për krahasim pa ndjeshmëri ndaj shkronjave të mëdha/vogla
    statuses = df['status'].fillna("").map(lambda x: x.strip())
    total = len(statuses)
    c = statuses.str.casefold().value_counts()
    completed = int(c.get('completed', 0))
    in_progress = int(c.get('in progress', 0))
    incomplete = int(c.get('incomplete', 0))
    return total, completed, in_progress, incomplete

def percent(part, total):
    return (part / total * 100.0) if total else 0.0

# ----------------------------------------
# Main UI entry point (called from main app)
# ----------------------------------------
def main(creds):
    sheet_client = GoogleSheetClient(creds)
    todo_app = TodoApp(sheet_client)

    selected = option_menu(
        menu_title="",
        options=["Create", "Read", "Update", "Delete"],
        icons=["plus-circle", "list-task", "pencil-square", "trash"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal"
    )

    # -------------------- CREATE --------------------
    if selected == "Create":
        st.header("📋 Add New Todo")
        todo_item = st.text_input("Enter your todo:")
        priority = st.selectbox("Select Priority", options=["Low", "Medium", "High"])
        if st.button("Add Todo"):
            if todo_item.strip():
                todo_app.create_todo(todo_item.strip(), priority)
                st.success("✅ Todo added successfully!")
            else:
                st.error("⚠️ Please enter a valid todo item.")

    # -------------------- READ --------------------
    elif selected == "Read":
        st.header("🏡 MyTodo List")
        headers, todos = todo_app.list_todos()

        if todos:
            df = build_df(headers, todos)

            # --- SEARCH: kërkim sipas emrit të 'todo' ---
            # Nëse kolona 'todo' nuk ekziston (emërtim tjetër), përdor kolonën e parë.
            todo_col = 'todo' if 'todo' in df.columns else df.columns[0]
            query = st.text_input("🔎 Kërko sipas emrit të detyrës", placeholder="Shkruaj një fjalë kyçe...").strip()
            filtered_df = df[df[todo_col].str.contains(query, case=False, na=False)] if query else df

            # --- METRICS & PROGRESS ---
            if 'status' in filtered_df.columns:
                total, completed, in_progress, incomplete = compute_stats(filtered_df)

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Total", total)
                with m2:
                    st.metric("Completed", f"{completed}", f"{percent(completed, total):.0f}%")
                with m3:
                    st.metric("In Progress", f"{in_progress}", f"{percent(in_progress, total):.0f}%")
                with m4:
                    st.metric("Incomplete", f"{incomplete}", f"{percent(incomplete, total):.0f}%")

                # Progres i përgjithshëm (përfundim)
                st.write("**Progress (Completed)**")
                st.progress(min(int(percent(completed, total)), 100))

            # --- DATAFRAME: më shumë rreshta në lartësi + stilim statusi ---
            try:
                styled = filtered_df.style.applymap(color_status, subset=["status"])
            except Exception:
                styled = filtered_df  # Nëse mungon 'status', shfaq pa stilim

            # Rrit lartësinë e tabelës (p.sh. 720px)
            st.dataframe(styled, use_container_width=True, height=720)
        else:
            st.info("ℹ️ No todos found.")

    # -------------------- UPDATE --------------------
    elif selected == "Update":
        st.header("🔏 Update a Todo")
        headers, todos = todo_app.list_todos()
        if todos:
            # Etiketa e listës: "todo | status"
            row_options = {
                f"{todo[0]} | {todo[4]}": i + 2
                for i, todo in enumerate(todos)
            }
            selected_row_str = st.selectbox("Select a todo to update", list(row_options.keys()))
            selected_row = row_options[selected_row_str]

            current_todo = todos[selected_row - 2][0]
            current_priority = todos[selected_row - 2][1]
            current_date_completed = todos[selected_row - 2][3]
            current_status = todos[selected_row - 2][4]

            new_todo = st.text_input("Update Todo", value=current_todo)
            priority_options = ["Low", "Medium", "High"]
            default_priority_index = priority_options.index(current_priority) if current_priority in priority_options else 0

            if current_date_completed:
                try:
                    default_date_completed = datetime.datetime.strptime(current_date_completed, '%d/%m/%Y').date()
                except ValueError:
                    default_date_completed = datetime.date.today()
            else:
                default_date_completed = datetime.date.today()

            status_options = ["Completed", "Incomplete", "In Progress"]
            default_status_index = status_options.index(current_status) if current_status in status_options else 1

            col1, col2, col3 = st.columns(3)
            with col1:
                new_priority = st.selectbox("Priority", options=priority_options, index=default_priority_index)
            with col2:
                new_date_completed = st.date_input("Date Completed", value=default_date_completed)
            with col3:
                new_status = st.selectbox("Status", options=status_options, index=default_status_index)

            if st.button("Update Todo"):
                todo_app.modify_todo(selected_row, new_todo.strip(), new_priority, new_date_completed, new_status)
                st.success("✅ Todo updated successfully!")
        else:
            st.info("ℹ️ No todos available to update.")

    # -------------------- DELETE --------------------
    elif selected == "Delete":
        st.header("🗑️ Delete a Todo")
        headers, todos = todo_app.list_todos()
        if todos:
            row_options = {
                f"{todo[0]} | {todo[4]}": i + 2
                for i, todo in enumerate(todos)
            }
            selected_row_str = st.selectbox("Select a todo to delete", list(row_options.keys()))
            selected_row = row_options[selected_row_str]
            if st.button("Delete Todo"):
                todo_app.remove_todo(selected_row)
                st.success("🗑️ Todo deleted successfully!")
        else:
            st.info("ℹ️ No todos available to delete.")
