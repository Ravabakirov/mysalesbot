import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_file="bot_data.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                phone TEXT NOT NULL,
                details TEXT,
                status TEXT NOT NULL,
                buy_date TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def add_client(self, fullname, phone, details, status, buy_date=None):
        created_at = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("""
            INSERT INTO clients (fullname, phone, details, status, buy_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fullname, phone, details, status, buy_date, created_at))
        self.conn.commit()

    def get_no_answer_clients(self):
        self.cursor.execute("SELECT id, fullname, phone, details FROM clients WHERE status = 'no_answer'")
        return self.cursor.fetchall()

    def get_clients_by_date(self, target_date):
        self.cursor.execute(
            "SELECT id, fullname, phone, details FROM clients WHERE buy_date = ? AND status = 'will_buy'",
            (target_date,)
        )
        return self.cursor.fetchall()

    def get_all_active_clients(self):
        self.cursor.execute("SELECT id, fullname, phone, status, buy_date FROM clients ORDER BY id DESC")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()

    def update_client_status(self, client_id, new_status, buy_date=None):
        self.cursor.execute("""
            UPDATE clients 
            SET status = ?, buy_date = ? 
            WHERE id = ?
        """, (new_status, buy_date, client_id))
        self.conn.commit()