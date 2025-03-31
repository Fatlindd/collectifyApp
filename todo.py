import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from gspread.exceptions import APIError
from google.oauth2 import service_account
import pandas as pd
import datetime

# ----------------------------------------
# Style for the status column
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
# Business logic wrapper
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
# Caching wrapper outside class (to fix UnhashableParamError)
# ----------------------------------------
@st.cache_data(ttl=60)
def get_cached_todos(sheet_client):
    todo_app = TodoApp(sheet_client)
    return todo_app.list_todos()

# ----------------------------------------
# Main UI logic
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
        headers, todos = get_cached_todos(sheet_client)
        if todos:
            df = pd.DataFrame(todos, columns=headers)
            df.index = range(1, len(df) + 1)
            styled_df = df.style.applymap(color_status, subset=["status"])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("ℹ️ No todos found.")

    # -------------------- UPDATE --------------------
    elif selected == "Update":
        st.header("🔏 Update a Todo")
        headers, todos = get_cached_todos(sheet_client)
        if todos:
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
        headers, todos = get_cached_todos(sheet_client)
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
