import streamlit as st
from streamlit_option_menu import option_menu
import gspread
from gspread.exceptions import APIError
from google.oauth2 import service_account
import pandas as pd
import datetime

# ----------------------------------------
# Utility: Style the "status" column
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
# Google Sheets Wrapper
# ----------------------------------------
class GoogleSheetClient:
    def __init__(self, creds, spreadsheet_name="Collectify", worksheet_name="Todo"):
        self.client = gspread.authorize(creds)
        try:
            self.sheet = self.client.open(spreadsheet_name).worksheet(worksheet_name)
        except APIError as e:
            st.error("🚫 Unable to access the Google Sheet. Please check credentials or sheet name.")
            st.exception(e)
            st.stop()

    def read_all_values(self):
        try:
            return self.sheet.get_all_values()
        except APIError as e:
            st.error("⚠️ Failed to read data from Google Sheet.")
            st.exception(e)
            return []

    def add_todo(self, todo_item, priority):
        try:
            date_added = datetime.datetime.now().strftime('%d/%m/%Y')
            date_completed = ""
            status = "Incomplete"
            self.sheet.append_row([todo_item, priority, date_added, date_completed, status])
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
# Todo App Logic
# ----------------------------------------
class TodoApp:
    def __init__(self, sheet_client):
        self.sheet_client = sheet_client

    @st.cache_data(ttl=60)
    def list_todos_cached(self):
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
# Main UI for Todo App
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

    elif selected == "Read":
        st.header("🏡 MyTodo List")
        headers, todos = todo_app.list_todos_cached()
        if todos:
            df = pd.DataFrame(todos, columns=headers)
            df.index = range(1, len(df) + 1)
            styled_df = df.style.applymap(color_status, subset=["status"])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("ℹ️ No todos found.")

    elif selected == "Update":
        st.header("🔏 Update a Todo")
        headers, todos = todo_app.list_todos_cached()
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
            try:
                default_priority_index = priority_options.index(current_priority)
            except ValueError:
                default_priority_index = 0

            if current_date_completed:
                try:
                    default_date_completed = datetime.datetime.strptime(current_date_completed, '%d/%m/%Y').date()
                except ValueError:
                    default_date_completed = datetime.date.today()
            else:
                default_date_completed = datetime.date.today()

            status_options = ["Completed", "Incomplete", "In Progress"]
            try:
                default_status_index = status_options.index(current_status)
            except ValueError:
                default_status_index = 1

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

    elif selected == "Delete":
        st.header("🗑️ Delete a Todo")
        headers, todos = todo_app.list_todos_cached()
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
