import sqlite3
from datetime import datetime

DB_NAME = 'inventory.db'

def connect_db():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)

def create_tables():
    """Creates the stock and transaction_log tables if they don't already exist."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL UNIQUE,
            title TEXT,
            language TEXT,
            quantity INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            enrolment_no TEXT,
            action TEXT NOT NULL CHECK (action IN ('in', 'out')),
            quantity INTEGER NOT NULL,
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name TEXT,
            remarks TEXT,
            phone TEXT,
            FOREIGN KEY (stock_id) REFERENCES stock (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Stock Functions ---

def add_stock(course_code, title, language, quantity):
    """Adds a new stock item to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO stock (course_code, title, language, quantity)
            VALUES (?, ?, ?, ?)
        ''', (course_code, title, language, int(quantity)))
        conn.commit()
        return True, "Stock added successfully."
    except sqlite3.IntegrityError:
        return False, f"Book '{course_code}' already exists."
    except Exception as e:
        return False, f"Error adding stock: {e}"
    finally:
        conn.close()

def get_all_stock(filters=None):
    """Retrieves all stock items, optionally applying filters."""
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT id, course_code, title, language, quantity FROM stock"
    params = []
    if filters:
        conditions = []
        for col, val in filters.items():
            if val:
                # Adjust column names for query if necessary
                db_col = col
                if col == "course_code": db_col = "course_code" # Example, ensure mapping if GUI names differ
                elif col == "title": db_col = "title"
                elif col == "language": db_col = "language"
                else: continue # Skip unknown filter keys

                conditions.append(f"{db_col} LIKE ?")
                params.append(f"%{val}%")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY course_code"
    cursor.execute(query, params)
    stock_items = cursor.fetchall()
    conn.close()
    return stock_items

def get_stock_by_id(stock_id):
    """Retrieves a specific stock item by its ID."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, course_code, title, language, quantity FROM stock WHERE id = ?", (stock_id,))
    stock_item = cursor.fetchone()
    conn.close()
    return stock_item

def get_stock_by_name(course_code):
    """Retrieves a specific stock item by its name."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, course_code, title, language, quantity FROM stock WHERE course_code = ?", (course_code,))
    stock_item = cursor.fetchone()
    conn.close()
    return stock_item

def update_stock(stock_id, course_code, title, language, quantity):
    """Updates an existing stock item."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE stock
            SET course_code = ?, title = ?, language = ?, quantity = ?
            WHERE id = ?
        ''', (course_code, title, language, int(quantity), stock_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Stock item not found or no changes made."
        return True, "Stock updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Course Code '{course_code}' might already exist for another item."
    except Exception as e:
        return False, f"Error updating stock: {e}"
    finally:
        conn.close()

def delete_stock(stock_id):
    """Deletes a stock item if no transactions are associated with it."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM transaction_log WHERE stock_id = ?", (stock_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Cannot delete stock: it has associated transactions. Please delete transactions first."
        
        cursor.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Stock item not found."
        return True, "Stock deleted successfully."
    except Exception as e:
        conn.rollback()
        return False, f"Error deleting stock: {e}"
    finally:
        conn.close()

# --- Internal Stock Quantity Adjustment ---
def _adjust_stock_quantity(cursor, stock_id, quantity_delta):
    """
    Adjusts stock quantity. Raises ValueError on issues.
    Assumes it's called within an existing transaction (cursor is passed).
    """
    cursor.execute("SELECT quantity FROM stock WHERE id = ?", (stock_id,))
    stock_row = cursor.fetchone()
    if not stock_row:
        raise ValueError(f"Stock item ID {stock_id} not found for quantity adjustment.")
    
    current_quantity = stock_row[0]
    new_quantity = current_quantity + quantity_delta
    
    if new_quantity < 0:
        raise ValueError(f"Stock for ID {stock_id} would be negative ({new_quantity}). Current: {current_quantity}, Change: {quantity_delta}.")
        
    cursor.execute("UPDATE stock SET quantity = ? WHERE id = ?", (new_quantity, stock_id))

# --- Transaction Functions ---

def add_transaction(stock_id, enrolment_no, action, quantity, name, remarks, phone):
    """Adds a new transaction and updates stock quantity."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return False, "Transaction quantity must be a positive integer."

        # Determine change in stock quantity based on action
        if action == 'out':
            stock_quantity_change = -quantity
        elif action == 'in':
            stock_quantity_change = quantity
        else:
            return False, "Invalid action. Must be 'in' or 'out'."

        # Adjust stock quantity (will raise ValueError if stock goes negative on 'out')
        _adjust_stock_quantity(cursor, stock_id, stock_quantity_change)

        # Record the transaction
        cursor.execute('''
            INSERT INTO transaction_log (stock_id, enrolment_no, action, quantity, transaction_time, name, remarks, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (stock_id, enrolment_no, action, quantity, datetime.now(), name, remarks, phone))
        
        conn.commit()
        return True, "Transaction added successfully and stock updated."
    except ValueError as e: # Catches errors from _adjust_stock_quantity or int conversion
        conn.rollback()
        return False, str(e)
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error: {e}"
    finally:
        conn.close()

def get_all_transactions(filters=None):
    """Retrieves all transactions, joined with stock to show course_code."""
    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT 
            t.id, 
            s.course_code, 
            t.enrolment_no, 
            t.action, 
            t.quantity, 
            STRFTIME('%Y-%m-%d %H:%M:%S', t.transaction_time), 
            t.name, 
            t.remarks, 
            t.phone,
            t.stock_id  -- Keep for internal use if needed (e.g. for delete)
        FROM transaction_log t
        JOIN stock s ON t.stock_id = s.id
    """
    params = []
    if filters:
        conditions = []
        # Supported filters: course_code, enrolment_no, action, name, remarks, phone
        for key, val in filters.items():
            if val:
                db_col = None
                if key == "course_code": db_col = "s.course_code"
                elif key == "enrolment_no": db_col = "t.enrolment_no"
                elif key == "action": db_col = "t.action" # Exact match might be better for 'action'
                elif key == "name": db_col = "t.name"
                elif key == "remarks": db_col = "t.remarks"
                elif key == "phone": db_col = "t.phone"
                
                if db_col:
                    if key == "action": # Use exact match for action
                        conditions.append(f"{db_col} = ?")
                        params.append(val)
                    else:
                        conditions.append(f"{db_col} LIKE ?")
                        params.append(f"%{val}%")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY t.transaction_time DESC"
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_transaction_by_id(transaction_id):
    """Retrieves a specific transaction by its ID, with course_code."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.id, t.stock_id, s.course_code, t.enrolment_no, t.action, t.quantity, 
            STRFTIME('%Y-%m-%d %H:%M:%S', t.transaction_time), t.name, t.remarks, t.phone
        FROM transaction_log t
        JOIN stock s ON t.stock_id = s.id
        WHERE t.id = ?
    """, (transaction_id,))
    transaction = cursor.fetchone() # Returns (trans_id, stock_id, course_code, ...)
    conn.close()
    return transaction

def delete_transaction(transaction_id):
    """Deletes a transaction and reverts the stock quantity change."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Get transaction details to revert stock quantity
        cursor.execute("SELECT stock_id, action, quantity FROM transaction_log WHERE id = ?", (transaction_id,))
        transaction_data = cursor.fetchone()
        if not transaction_data:
            return False, "Transaction not found."

        stock_id, action, trans_quantity = transaction_data
        stock_quantity_change = 0
        if action == 'in': # Reverting an 'in' means decreasing stock
            stock_quantity_change = -trans_quantity
        elif action == 'out': # Reverting an 'out' means increasing stock
            stock_quantity_change = trans_quantity
        
        # Adjust stock quantity. _adjust_stock_quantity will raise ValueError if it goes negative.
        _adjust_stock_quantity(cursor, stock_id, stock_quantity_change)

        # Delete the transaction
        cursor.execute("DELETE FROM transaction_log WHERE id = ?", (transaction_id,))
        conn.commit()
        if cursor.rowcount == 0: # Should not happen if fetchone() succeeded
             return False, "Transaction not found during delete."
        return True, "Transaction deleted successfully and stock updated."
    except ValueError as e: # From _adjust_stock_quantity
        conn.rollback()
        return False, f"Failed to adjust stock: {e}. Transaction not deleted."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error: {e}"
    finally:
        conn.close()

def update_transaction_details(transaction_id, enrolment_no, name, remarks, phone):
    """Updates non-critical details of a transaction (enrolment_no, name, remarks, phone)."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE transaction_log
            SET enrolment_no = ?, name = ?, remarks = ?, phone = ?
            WHERE id = ?
        ''', (enrolment_no, name, remarks, phone, transaction_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Transaction not found or no changes made."
        return True, "Transaction details updated successfully."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error updating transaction: {e}"
    finally:
        conn.close()

if __name__ == '__main__':
    create_tables()
    print("Database 'inventory.db' and tables created/ensured.")
    # You can add some initial data for testing if you like:
    # add_stock("Python Basics", "CS100", "English", 50)
    # add_stock("Advanced Java", "CS305", "English", 30)
    # print(get_all_stock())
    # stock_item = get_stock_by_name("Python Basics")
    # if stock_item:
    #    add_transaction(stock_item[0], "PID001", "out", 2, "John Doe", "S1001", "123-456-7890")
    #    add_transaction(stock_item[0], "PID002", "in", 5, "Restock", "WAREHOUSE", "N/A")
    # print(get_all_transactions()) 