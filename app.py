import tkinter as tk
from tkinter import ttk, messagebox
import database as db # Assuming database.py is in the same directory

class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Book Inventory Management")
        self.root.geometry("1200x800")

        # Initialize database and tables
        db.create_tables()

        # Styling
        style = ttk.Style()
        style.theme_use('clam') # Or 'alt', 'default', 'classic'
        style.configure("Treeview.Heading", font=('Calibri', 10,'bold'))

        # Notebook for tabs
        self.notebook = ttk.Notebook(root)
        
        self.stock_tab = ttk.Frame(self.notebook)
        self.transactions_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.stock_tab, text='Stock Management')
        self.notebook.add(self.transactions_tab, text='Transaction Log')
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        self.selected_stock_id = None
        self.selected_transaction_id = None
        self.selected_transaction_stock_id = None # For transaction updates/deletes

        self.create_stock_widgets()
        self.create_transaction_widgets()

        self.refresh_stock_view()
        self.refresh_transaction_view()
        self.populate_course_code_combobox()


    # --- Stock Tab ---
    def create_stock_widgets(self):
        # --- Filter Frame ---
        filter_frame_stock = ttk.LabelFrame(self.stock_tab, text="Filter Stock", padding=10)
        filter_frame_stock.pack(fill="x", padx=10, pady=5)

        ttk.Label(filter_frame_stock, text="Course Code:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.stock_filter_course_code = ttk.Entry(filter_frame_stock, width=30)
        self.stock_filter_course_code.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame_stock, text="Title:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.stock_filter_title = ttk.Entry(filter_frame_stock, width=20)
        self.stock_filter_title.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(filter_frame_stock, text="Language:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.stock_filter_language = ttk.Entry(filter_frame_stock, width=15)
        self.stock_filter_language.grid(row=0, column=5, padx=5, pady=5)

        ttk.Button(filter_frame_stock, text="Filter", command=self.filter_stock_view).grid(row=0, column=6, padx=10, pady=5)
        ttk.Button(filter_frame_stock, text="Clear Filters", command=self.clear_stock_filters_and_refresh).grid(row=0, column=7, padx=5, pady=5)

        # --- Treeview Frame ---
        tree_frame_stock = ttk.Frame(self.stock_tab)
        tree_frame_stock.pack(fill="both", expand=True, padx=10, pady=5)

        self.stock_tree = ttk.Treeview(tree_frame_stock, columns=("ID", "Course Code", "Title", "Language", "Quantity"), show="headings")
        self.stock_tree.heading("ID", text="ID")
        self.stock_tree.heading("Course Code", text="Course Code")
        self.stock_tree.heading("Title", text="Title")
        self.stock_tree.heading("Language", text="Language")
        self.stock_tree.heading("Quantity", text="Quantity")

        self.stock_tree.column("ID", width=50, anchor="center")
        self.stock_tree.column("Course Code", width=250)
        self.stock_tree.column("Title", width=150)
        self.stock_tree.column("Language", width=100)
        self.stock_tree.column("Quantity", width=80, anchor="center")

        stock_scrollbar = ttk.Scrollbar(tree_frame_stock, orient="vertical", command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=stock_scrollbar.set)
        stock_scrollbar.pack(side="right", fill="y")
        self.stock_tree.pack(fill="both", expand=True)
        self.stock_tree.bind("<<TreeviewSelect>>", self.on_stock_select)

        # --- Form Frame ---
        form_frame_stock = ttk.LabelFrame(self.stock_tab, text="Manage Stock Item", padding=10)
        form_frame_stock.pack(fill="x", padx=10, pady=10)

        ttk.Label(form_frame_stock, text="Course Code:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.stock_course_code_entry = ttk.Entry(form_frame_stock, width=40)
        self.stock_course_code_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_stock, text="Title:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.stock_title_entry = ttk.Entry(form_frame_stock, width=40)
        self.stock_title_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_stock, text="Language:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.stock_language_entry = ttk.Entry(form_frame_stock, width=25)
        self.stock_language_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_stock, text="Quantity:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.stock_quantity_entry = ttk.Entry(form_frame_stock, width=10)
        self.stock_quantity_entry.grid(row=1, column=3, padx=5, pady=2, sticky="w")
        
        form_frame_stock.columnconfigure(1, weight=1)
        form_frame_stock.columnconfigure(3, weight=1)


        # --- Button Frame ---
        button_frame_stock = ttk.Frame(self.stock_tab, padding=5)
        button_frame_stock.pack(fill="x", padx=10, pady=5)

        ttk.Button(button_frame_stock, text="Add Stock", command=self.add_stock_item).pack(side="left", padx=5)
        ttk.Button(button_frame_stock, text="Update Selected", command=self.update_stock_item).pack(side="left", padx=5)
        ttk.Button(button_frame_stock, text="Delete Selected", command=self.delete_stock_item).pack(side="left", padx=5)
        ttk.Button(button_frame_stock, text="Clear Form", command=self.clear_stock_form).pack(side="left", padx=5)
        ttk.Button(button_frame_stock, text="Refresh View", command=self.refresh_stock_view).pack(side="right", padx=5)

    def clear_stock_filters_and_refresh(self):
        self.stock_filter_course_code.delete(0, tk.END)
        self.stock_filter_title.delete(0, tk.END)
        self.stock_filter_language.delete(0, tk.END)
        self.refresh_stock_view()

    def filter_stock_view(self):
        filters = {
            "course_code": self.stock_filter_course_code.get(),
            "title": self.stock_filter_title.get(),
            "language": self.stock_filter_language.get()
        }
        self.refresh_stock_view(filters=filters)

    def on_stock_select(self, event=None):
        selected_items = self.stock_tree.selection()
        if not selected_items:
            self.selected_stock_id = None
            self.clear_stock_form(clear_selection=False) # Don't reset selected_stock_id again
            return

        item = self.stock_tree.item(selected_items[0])
        values = item['values']
        
        self.selected_stock_id = values[0]
        self.stock_course_code_entry.delete(0, tk.END)
        self.stock_course_code_entry.insert(0, values[1])
        self.stock_title_entry.delete(0, tk.END)
        self.stock_title_entry.insert(0, values[2])
        self.stock_language_entry.delete(0, tk.END)
        self.stock_language_entry.insert(0, values[3])
        self.stock_quantity_entry.delete(0, tk.END)
        self.stock_quantity_entry.insert(0, values[4])

    def clear_stock_form(self, clear_selection=True):
        self.stock_course_code_entry.delete(0, tk.END)
        self.stock_title_entry.delete(0, tk.END)
        self.stock_language_entry.delete(0, tk.END)
        self.stock_quantity_entry.delete(0, tk.END)
        if clear_selection:
            self.selected_stock_id = None
            if self.stock_tree.selection(): # Deselect from tree
                self.stock_tree.selection_remove(self.stock_tree.selection()[0])


    def refresh_stock_view(self, filters=None):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        stock_data = db.get_all_stock(filters=filters)
        for row in stock_data:
            self.stock_tree.insert("", "end", values=row)
        self.populate_course_code_combobox() # Update combobox in transaction tab

    def add_stock_item(self):
        course_code = self.stock_course_code_entry.get()
        title = self.stock_title_entry.get()
        language = self.stock_language_entry.get()
        quantity_str = self.stock_quantity_entry.get()

        if not course_code or not quantity_str:
            messagebox.showerror("Input Error", "Course Code and Quantity are required.")
            return
        try:
            quantity = int(quantity_str)
            if quantity < 0:
                messagebox.showerror("Input Error", "Quantity cannot be negative.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Quantity must be a valid integer.")
            return

        success, message = db.add_stock(course_code, title, language, quantity)
        if success:
            messagebox.showinfo("Success", message)
            self.refresh_stock_view()
            self.clear_stock_form()
        else:
            messagebox.showerror("Database Error", message)

    def update_stock_item(self):
        if self.selected_stock_id is None:
            messagebox.showwarning("Selection Error", "Please select a stock item to update.")
            return

        course_code = self.stock_course_code_entry.get()
        title = self.stock_title_entry.get()
        language = self.stock_language_entry.get()
        quantity_str = self.stock_quantity_entry.get()

        if not course_code or not quantity_str:
            messagebox.showerror("Input Error", "Course Code and Quantity are required.")
            return
        try:
            quantity = int(quantity_str)
            if quantity < 0:
                messagebox.showerror("Input Error", "Quantity cannot be negative.")
                return
        except ValueError:
            messagebox.showerror("Input Error", "Quantity must be a valid integer.")
            return
        
        success, message = db.update_stock(self.selected_stock_id, course_code, title, language, quantity)
        if success:
            messagebox.showinfo("Success", message)
            self.refresh_stock_view()
            self.clear_stock_form()
        else:
            messagebox.showerror("Database Error", message)
            
    def delete_stock_item(self):
        if self.selected_stock_id is None:
            messagebox.showwarning("Selection Error", "Please select a stock item to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this stock item?"):
            success, message = db.delete_stock(self.selected_stock_id)
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_stock_view()
                self.clear_stock_form()
            else:
                messagebox.showerror("Error", message)

    # --- Transaction Tab ---
    def create_transaction_widgets(self):
        # --- Filter Frame ---
        filter_frame_trans = ttk.LabelFrame(self.transactions_tab, text="Filter Transactions", padding=10)
        filter_frame_trans.pack(fill="x", padx=10, pady=5)

        ttk.Label(filter_frame_trans, text="Course Code:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.trans_filter_course_code = ttk.Entry(filter_frame_trans, width=20)
        self.trans_filter_course_code.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame_trans, text="Enrolment No:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.trans_filter_enrolment_no = ttk.Entry(filter_frame_trans, width=15)
        self.trans_filter_enrolment_no.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filter_frame_trans, text="Action (in/out):").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.trans_filter_action = ttk.Combobox(filter_frame_trans, values=["", "in", "out"], width=8, state="readonly")
        self.trans_filter_action.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(filter_frame_trans, text="Filter", command=self.filter_transaction_view).grid(row=0, column=6, padx=10, pady=5)
        ttk.Button(filter_frame_trans, text="Clear Filters", command=self.clear_transaction_filters_and_refresh).grid(row=0, column=7, padx=5, pady=5)


        # --- Treeview Frame ---
        tree_frame_trans = ttk.Frame(self.transactions_tab)
        tree_frame_trans.pack(fill="both", expand=True, padx=10, pady=5)

        self.trans_tree = ttk.Treeview(tree_frame_trans, columns=("ID", "Course Code", "Enrolment No", "Action", "Qty", "Datetime", "Name", "Remarks", "Phone"), show="headings")
        self.trans_tree.heading("ID", text="Trans ID")
        self.trans_tree.heading("Course Code", text="Course Code")
        self.trans_tree.heading("Enrolment No", text="Enrolment No")
        self.trans_tree.heading("Action", text="Action")
        self.trans_tree.heading("Qty", text="Quantity")
        self.trans_tree.heading("Datetime", text="Timestamp")
        self.trans_tree.heading("Name", text="Contact Name")
        self.trans_tree.heading("Remarks", text="Remarks.")
        self.trans_tree.heading("Phone", text="Phone")

        self.trans_tree.column("ID", width=60, anchor="center")
        self.trans_tree.column("Course Code", width=180)
        self.trans_tree.column("Enrolment No", width=80)
        self.trans_tree.column("Action", width=60, anchor="center")
        self.trans_tree.column("Qty", width=60, anchor="center")
        self.trans_tree.column("Datetime", width=140)
        self.trans_tree.column("Name", width=120)
        self.trans_tree.column("Remarks", width=100)
        self.trans_tree.column("Phone", width=100)
        
        trans_scrollbar = ttk.Scrollbar(tree_frame_trans, orient="vertical", command=self.trans_tree.yview)
        self.trans_tree.configure(yscrollcommand=trans_scrollbar.set)
        trans_scrollbar.pack(side="right", fill="y")
        self.trans_tree.pack(fill="both", expand=True)
        self.trans_tree.bind("<<TreeviewSelect>>", self.on_transaction_select)

        # --- Form Frame ---
        form_frame_trans = ttk.LabelFrame(self.transactions_tab, text="Manage Transaction", padding=10)
        form_frame_trans.pack(fill="x", padx=10, pady=10)

        ttk.Label(form_frame_trans, text="Course Code:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.trans_course_code_combo = ttk.Combobox(form_frame_trans, width=38, state="readonly")
        self.trans_course_code_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_trans, text="Action:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.trans_action_combo = ttk.Combobox(form_frame_trans, values=["in", "out"], width=10, state="readonly")
        self.trans_action_combo.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        self.trans_action_combo.set("out") # Default

        ttk.Label(form_frame_trans, text="Quantity:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.trans_quantity_entry = ttk.Entry(form_frame_trans, width=10)
        self.trans_quantity_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame_trans, text="Enrolment No:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.trans_enrolment_no_entry = ttk.Entry(form_frame_trans, width=25)
        self.trans_enrolment_no_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        
        ttk.Label(form_frame_trans, text="Contact Name:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.trans_name_entry = ttk.Entry(form_frame_trans, width=40)
        self.trans_name_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_trans, text="Remarks:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.trans_remarks_entry = ttk.Entry(form_frame_trans, width=25)
        self.trans_remarks_entry.grid(row=2, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame_trans, text="Phone:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.trans_phone_entry = ttk.Entry(form_frame_trans, width=40)
        self.trans_phone_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        form_frame_trans.columnconfigure(1, weight=1)
        form_frame_trans.columnconfigure(3, weight=1)

        # --- Button Frame ---
        button_frame_trans = ttk.Frame(self.transactions_tab, padding=5)
        button_frame_trans.pack(fill="x", padx=10, pady=5)

        ttk.Button(button_frame_trans, text="Add Transaction", command=self.add_transaction_item).pack(side="left", padx=5)
        ttk.Button(button_frame_trans, text="Update Selected (Details)", command=self.update_transaction_item).pack(side="left", padx=5)
        ttk.Button(button_frame_trans, text="Delete Selected", command=self.delete_transaction_item).pack(side="left", padx=5)
        ttk.Button(button_frame_trans, text="Clear Form", command=self.clear_transaction_form).pack(side="left", padx=5)
        ttk.Button(button_frame_trans, text="Refresh View", command=self.refresh_transaction_view).pack(side="right", padx=5)

    def clear_transaction_filters_and_refresh(self):
        self.trans_filter_course_code.delete(0, tk.END)
        self.trans_filter_enrolment_no.delete(0, tk.END)
        self.trans_filter_action.set("")
        self.refresh_transaction_view()

    def filter_transaction_view(self):
        filters = {
            "course_code": self.trans_filter_course_code.get(),
            "enrolment_no": self.trans_filter_enrolment_no.get(),
            "action": self.trans_filter_action.get()
            # Add more filters here if needed, e.g., name, remarks
        }
        self.refresh_transaction_view(filters=filters)

    def populate_course_code_combobox(self):
        stock_items = db.get_all_stock()
        course_codes = [item[1] for item in stock_items] # item[1] is course_code
        self.trans_course_code_combo['values'] = course_codes
        if course_codes:
            self.trans_course_code_combo.set(course_codes[0]) # Default to first book
        else:
            self.trans_course_code_combo.set("")


    def on_transaction_select(self, event=None):
        selected_items = self.trans_tree.selection()
        if not selected_items:
            self.selected_transaction_id = None
            self.selected_transaction_stock_id = None
            self.clear_transaction_form(clear_selection=False)
            return

        item = self.trans_tree.item(selected_items[0])
        values = item['values'] # (Trans ID, Course Code, Enrolment No, Action, Qty, Datetime, Name, Remarks, Phone)
                                # The get_all_transactions also returns stock_id as the last (hidden) element if needed.
                                # For now, we fetch transaction by ID to get all details including stock_id for updates.
        
        self.selected_transaction_id = values[0]
        
        # Fetch full transaction data to get stock_id and ensure data consistency
        # The treeview might not have stock_id directly visible or easily accessible for logic
        full_trans_data = db.get_transaction_by_id(self.selected_transaction_id)
        # full_trans_data: (trans_id, stock_id, course_code, enrolment_no, action, quantity, ...)
        if not full_trans_data:
            messagebox.showerror("Error", "Could not retrieve transaction details.")
            self.clear_transaction_form()
            return

        self.selected_transaction_stock_id = full_trans_data[1] # stock_id

        self.trans_course_code_combo.set(full_trans_data[2]) # Course Code
        self.trans_action_combo.set(full_trans_data[4])    # Action
        self.trans_quantity_entry.delete(0, tk.END)
        self.trans_quantity_entry.insert(0, full_trans_data[5]) # Quantity
        self.trans_enrolment_no_entry.delete(0, tk.END)
        self.trans_enrolment_no_entry.insert(0, full_trans_data[3]) # Enrolment No
        self.trans_name_entry.delete(0, tk.END)
        self.trans_name_entry.insert(0, full_trans_data[7]) # Name
        self.trans_remarks_entry.delete(0, tk.END)
        self.trans_remarks_entry.insert(0, full_trans_data[8]) # Remarks
        self.trans_phone_entry.delete(0, tk.END)
        self.trans_phone_entry.insert(0, full_trans_data[9]) # Phone

        # Disable fields not updatable via "Update Details"
        self.trans_course_code_combo.config(state="disabled")
        self.trans_action_combo.config(state="disabled")
        self.trans_quantity_entry.config(state="disabled")


    def clear_transaction_form(self, clear_selection=True):
        if clear_selection:
            self.selected_transaction_id = None
            self.selected_transaction_stock_id = None
            if self.trans_tree.selection(): # Deselect from tree
                self.trans_tree.selection_remove(self.trans_tree.selection()[0])
        
        # Re-enable fields that might have been disabled by on_transaction_select
        self.trans_course_code_combo.config(state="readonly") # Or "normal" if typing is allowed
        self.populate_course_code_combobox() # Repopulate and set default
        self.trans_action_combo.config(state="readonly")
        self.trans_action_combo.set("out")
        self.trans_quantity_entry.config(state="normal")

        self.trans_quantity_entry.delete(0, tk.END)
        self.trans_enrolment_no_entry.delete(0, tk.END)
        self.trans_name_entry.delete(0, tk.END)
        self.trans_remarks_entry.delete(0, tk.END)
        self.trans_phone_entry.delete(0, tk.END)


    def refresh_transaction_view(self, filters=None):
        for item in self.trans_tree.get_children():
            self.trans_tree.delete(item)
        
        transaction_data = db.get_all_transactions(filters=filters)
        for row in transaction_data:
            # The last element row[-1] is stock_id, we don't display it directly in main columns
            self.trans_tree.insert("", "end", values=row[:-1]) 
        self.clear_transaction_form() # Clear form and selection after refresh

    def add_transaction_item(self):
        course_code_selected = self.trans_course_code_combo.get()
        action = self.trans_action_combo.get()
        quantity_str = self.trans_quantity_entry.get()
        enrolment_no = self.trans_enrolment_no_entry.get()
        name = self.trans_name_entry.get()
        remarks = self.trans_remarks_entry.get()
        phone = self.trans_phone_entry.get()

        if not course_code_selected or not action or not quantity_str:
            messagebox.showerror("Input Error", "Course Code, Action, and Quantity are required.")
            return
        
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                 messagebox.showerror("Input Error", "Quantity must be a positive integer.")
                 return
        except ValueError:
            messagebox.showerror("Input Error", "Quantity must be a valid integer.")
            return

        stock_item = db.get_stock_by_name(course_code_selected)
        if not stock_item:
            messagebox.showerror("Input Error", f"Stock item '{course_code_selected}' not found.")
            return
        stock_id = stock_item[0]

        success, message = db.add_transaction(stock_id, enrolment_no, action, quantity, name, remarks, phone)
        if success:
            messagebox.showinfo("Success", message)
            self.refresh_transaction_view()
            self.refresh_stock_view() # Stock quantity changed
            self.clear_transaction_form()
        else:
            messagebox.showerror("Error", message)

    def update_transaction_item(self):
        if self.selected_transaction_id is None:
            messagebox.showwarning("Selection Error", "Please select a transaction to update.")
            return

        # Only these fields are updatable via this function
        enrolment_no = self.trans_enrolment_no_entry.get()
        name = self.trans_name_entry.get()
        remarks = self.trans_remarks_entry.get()
        phone = self.trans_phone_entry.get()

        # Note: Book, Action, Quantity are not updated here to keep stock logic simple.
        # User should delete and re-add if those need to change.
        
        success, message = db.update_transaction_details(self.selected_transaction_id, enrolment_no, name, remarks, phone)
        if success:
            messagebox.showinfo("Success", message)
            self.refresh_transaction_view()
            # No need to refresh stock view as only non-quantity affecting details changed
            self.clear_transaction_form()
        else:
            messagebox.showerror("Error", message)


    def delete_transaction_item(self):
        if self.selected_transaction_id is None:
            messagebox.showwarning("Selection Error", "Please select a transaction to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction? This will also adjust stock levels."):
            success, message = db.delete_transaction(self.selected_transaction_id)
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_transaction_view()
                self.refresh_stock_view() # Stock quantity changed
                self.clear_transaction_form()
            else:
                messagebox.showerror("Error", message)


if __name__ == "__main__":
    main_root = tk.Tk()
    app = InventoryApp(main_root)
    main_root.mainloop() 