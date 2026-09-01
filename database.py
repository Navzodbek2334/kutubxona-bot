import sqlite3

class Database:
    def __init__(self, db_file="database.db"):
        # timeout=30 qo'shildi (baza band bo'lsa 30 sek kutadi, qotmaydi)
        self.conn = sqlite3.connect(db_file, check_same_thread=False, timeout=30)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Foydalanuvchilar jadvali
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Adminlar jadvali
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'admin'
            )
        """)

        # Bo'limlar (kategoriyalar) jadvali
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)

        # Kitoblar jadvali
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                title TEXT NOT NULL,
                part_name TEXT NOT NULL,
                file_id TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    # --- USER METODLARI ---
    def add_user(self, user_id, full_name, username):
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user_id, full_name, username)
        )
        self.conn.commit()

    # --- ADMIN METODLARI ---
    def add_admin(self, user_id, role="admin"):
        self.cursor.execute(
            "INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)",
            (user_id, role)
        )
        self.conn.commit()

    def remove_admin(self, user_id):
        self.cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_admin(self, user_id):
        self.cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def get_all_admins(self):
        self.cursor.execute("SELECT user_id, role FROM admins")
        return self.cursor.fetchall()

    # --- BO'LIM METODLARI ---
    def add_category(self, name):
        self.cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        self.conn.commit()

    def get_categories(self):
        self.cursor.execute("SELECT id, name FROM categories")
        return self.cursor.fetchall()

    def update_category(self, cat_id, new_name):
        self.cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cat_id))
        self.conn.commit()

    def delete_category(self, cat_id):
        self.cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        self.cursor.execute("DELETE FROM books WHERE category_id = ?", (cat_id,))
        self.conn.commit()

    # --- KITOB METODLARI ---
    def add_book(self, category_id, title, part_name, file_id):
        self.cursor.execute(
            "INSERT INTO books (category_id, title, part_name, file_id) VALUES (?, ?, ?, ?)",
            (category_id, title, part_name, file_id)
        )
        self.conn.commit()

    def get_unique_books_by_category(self, category_id):
        self.cursor.execute(
            "SELECT DISTINCT title FROM books WHERE category_id = ?", (category_id,)
        )
        return self.cursor.fetchall()

    def get_parts_by_title(self, category_id, title):
        self.cursor.execute(
            "SELECT id, part_name FROM books WHERE category_id = ? AND title = ?",
            (category_id, title)
        )
        return self.cursor.fetchall()

    def get_book_by_id(self, book_id):
        self.cursor.execute("SELECT id, category_id, title, part_name, file_id FROM books WHERE id = ?", (book_id,))
        return self.cursor.fetchone()

    def update_book(self, book_id, title, part_name):
        self.cursor.execute("UPDATE books SET title = ?, part_name = ? WHERE id = ?", (title, part_name, book_id))
        self.conn.commit()

    def update_book_file(self, book_id, new_file_id):
        self.cursor.execute("UPDATE books SET file_id = ? WHERE id = ?", (new_file_id, book_id))
        self.conn.commit()

    def delete_book(self, book_id):
        self.cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()

    def search_books(self, query):
        self.cursor.execute(
            "SELECT id, title, part_name FROM books WHERE title LIKE ?",
            (f"%{query}%",)
        )
        return self.cursor.fetchall()

    def get_stats(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        users_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM categories")
        categories_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM books")
        books_count = self.cursor.fetchone()[0]
        
        return {
            "users": users_count,
            "categories": categories_count,
            "books": books_count
        }

db = Database()