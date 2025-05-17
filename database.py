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
            book_name TEXT NOT NULL UNIQUE,
            course_code TEXT,
            language TEXT,
            quantity INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            person_id TEXT,
            action TEXT NOT NULL CHECK (action IN ('in', 'out')),
            quantity INTEGER NOT NULL,
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name TEXT,
            student_no TEXT,
            phone TEXT,
            FOREIGN KEY (stock_id) REFERENCES stock (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Stock Functions ---

def add_stock(book_name, course_code, language, quantity):
    """Adds a new stock item to the database."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO stock (book_name, course_code, language, quantity)
            VALUES (?, ?, ?, ?)
        ''', (book_name, course_code, language, int(quantity)))
        conn.commit()
        return True, "Stock added successfully."
    except sqlite3.IntegrityError:
        return False, f"Book '{book_name}' already exists."
    except Exception as e:
        return False, f"Error adding stock: {e}"
    finally:
        conn.close()

def get_all_stock(filters=None):
    """Retrieves all stock items, optionally applying filters."""
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT id, book_name, course_code, language, quantity FROM stock"
    params = []
    if filters:
        conditions = []
        for col, val in filters.items():
            if val:
                # Adjust column names for query if necessary
                db_col = col
                if col == "book_name": db_col = "book_name" # Example, ensure mapping if GUI names differ
                elif col == "course_code": db_col = "course_code"
                elif col == "language": db_col = "language"
                else: continue # Skip unknown filter keys

                conditions.append(f"{db_col} LIKE ?")
                params.append(f"%{val}%")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY book_name"
    cursor.execute(query, params)
    stock_items = cursor.fetchall()
    conn.close()
    return stock_items

def get_stock_by_id(stock_id):
    """Retrieves a specific stock item by its ID."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, book_name, course_code, language, quantity FROM stock WHERE id = ?", (stock_id,))
    stock_item = cursor.fetchone()
    conn.close()
    return stock_item

def get_stock_by_name(book_name):
    """Retrieves a specific stock item by its name."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, book_name, course_code, language, quantity FROM stock WHERE book_name = ?", (book_name,))
    stock_item = cursor.fetchone()
    conn.close()
    return stock_item

def update_stock(stock_id, book_name, course_code, language, quantity):
    """Updates an existing stock item."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE stock
            SET book_name = ?, course_code = ?, language = ?, quantity = ?
            WHERE id = ?
        ''', (book_name, course_code, language, int(quantity), stock_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Stock item not found or no changes made."
        return True, "Stock updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Book name '{book_name}' might already exist for another item."
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

def add_transaction(stock_id, person_id, action, quantity, name, student_no, phone):
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
            INSERT INTO transaction_log (stock_id, person_id, action, quantity, transaction_time, name, student_no, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (stock_id, person_id, action, quantity, datetime.now(), name, student_no, phone))
        
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
    """Retrieves all transactions, joined with stock to show book_name."""
    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT 
            t.id, 
            s.book_name, 
            t.person_id, 
            t.action, 
            t.quantity, 
            STRFTIME('%Y-%m-%d %H:%M:%S', t.transaction_time), 
            t.name, 
            t.student_no, 
            t.phone,
            t.stock_id  -- Keep for internal use if needed (e.g. for delete)
        FROM transaction_log t
        JOIN stock s ON t.stock_id = s.id
    """
    params = []
    if filters:
        conditions = []
        # Supported filters: book_name, person_id, action, name, student_no, phone
        for key, val in filters.items():
            if val:
                db_col = None
                if key == "book_name": db_col = "s.book_name"
                elif key == "person_id": db_col = "t.person_id"
                elif key == "action": db_col = "t.action" # Exact match might be better for 'action'
                elif key == "name": db_col = "t.name"
                elif key == "student_no": db_col = "t.student_no"
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
    """Retrieves a specific transaction by its ID, with book_name."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.id, t.stock_id, s.book_name, t.person_id, t.action, t.quantity, 
            STRFTIME('%Y-%m-%d %H:%M:%S', t.transaction_time), t.name, t.student_no, t.phone
        FROM transaction_log t
        JOIN stock s ON t.stock_id = s.id
        WHERE t.id = ?
    """, (transaction_id,))
    transaction = cursor.fetchone() # Returns (trans_id, stock_id, book_name, ...)
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

def update_transaction_details(transaction_id, person_id, name, student_no, phone):
    """Updates non-critical details of a transaction (person_id, name, student_no, phone)."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE transaction_log
            SET person_id = ?, name = ?, student_no = ?, phone = ?
            WHERE id = ?
        ''', (person_id, name, student_no, phone, transaction_id))
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