#database.py

import sqlite3
from datetime import datetime
from pathlib import Path
import threading

db_name = Path(__file__).with_name("chat.db")
DEFAULT_ROOM = "lobby"

db_lock = threading.Lock()

def get_connection():
    conn = sqlite3.connect(db_name, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn
def init_db():
    with db_lock:
        conn = get_connection()
        imlec = conn.cursor()
        
        imlec.execute("""
        CREATE TABLE IF NOT EXISTS mesajlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER,
            mesaj TEXT NOT NULL,
            saat TEXT NOT NULL,
            room TEXT
    )
    """)
        imlec.execute("""
        CREATE TABLE IF NOT EXISTS odalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
    )
    """)
        imlec.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'user'            
    )
    """)
        imlec.execute(
            "INSERT OR IGNORE INTO odalar (name, created_at) VALUES (?, ?)",
            (DEFAULT_ROOM, datetime.now().strftime("%H:%M"))
        )
        imlec.execute("PRAGMA table_info(mesajlar)")
        message_columns = [row[1] for row in imlec.fetchall()]
        if "room" not in message_columns:
            imlec.execute(
                "ALTER TABLE mesajlar ADD COLUMN room TEXT DEFAULT 'lobby'"
            )

        conn.commit()
        conn.close()
def register(username, password_hash, salt):
    with db_lock:
        conn = get_connection()
        imlec = conn.cursor()
        try:
            sorgu = "INSERT INTO kullanicilar (username, password_hash, salt) VALUES (?,?,?)"
            imlec.execute(sorgu, (username, password_hash, salt))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
def login(username, password_hash):
    conn = get_connection()
    imlec = conn.cursor()
    sorgu = "SELECT id, rol FROM kullanicilar WHERE username = ? AND password_hash = ?"
    veriler = (username,password_hash)
    imlec.execute(sorgu,veriler)
    sonuc = imlec.fetchone()
    conn.close()
    if sonuc:
        return sonuc[0], sonuc[1]
    return None
def get_user_credentials(username):
    conn = get_connection()
    imlec = conn.cursor()
    sorgu = "SELECT password_hash, salt FROM kullanicilar WHERE username = ?"
    veriler = (username,)

    imlec.execute(sorgu,veriler)
    sonuc = imlec.fetchone()
    conn.close()
    if sonuc:
        return sonuc[0], sonuc[1]
    return None
def add_room(room_name):
    with db_lock:
        conn = get_connection()
        imlec = conn.cursor()
        saat = datetime.now().strftime("%H:%M")
        imlec.execute(
            "INSERT OR IGNORE INTO odalar (name, created_at) VALUES (?, ?)",
            (room_name, saat)
        )
        conn.commit()
        conn.close()

def get_room_names():
    conn = get_connection()
    imlec = conn.cursor()
    imlec.execute("SELECT name FROM odalar ORDER BY name")
    room_names = [row[0] for row in imlec.fetchall()]
    conn.close()
    return room_names

def add_message(sender_id, mesaj, receiver_id=None, room=DEFAULT_ROOM):
    if sender_id is None:
        return

    if room:
        add_room(room)

    with db_lock:
        conn = get_connection()
        imlec = conn.cursor()
        saat = datetime.now().strftime("%H:%M")
        sorgu = """
            INSERT INTO mesajlar
            (sender_id, receiver_id, mesaj, saat, room)
            VALUES (?, ?, ?, ?, ?)
        """
        imlec.execute(sorgu, (sender_id, receiver_id, mesaj, saat, room))
        conn.commit()
        conn.close()
        
def update_username(old_username,new_username):
    with db_lock:
        conn = get_connection()
        imlec = conn.cursor()
        try:
            imlec.execute("UPDATE kullanicilar SET username = ? WHERE username = ?",(new_username,old_username))
            
            if imlec.rowcount == 0:
                conn.close()
                return False
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
def get_last_messages(limit=15, room=None):
    conn = get_connection()
    imlec = conn.cursor()

    if room is None:
        imlec.execute(
            "SELECT k.username, m.mesaj, m.receiver_id, m.saat, m.room FROM mesajlar m JOIN kullanicilar k ON m.sender_id = k.id ORDER BY m.id DESC LIMIT ?",
            (limit,)
        )
    else:
        imlec.execute(
            "SELECT k.username, m.mesaj, m.receiver_id, m.saat, m.room FROM mesajlar m JOIN kullanicilar k ON m.sender_id = k.id WHERE m.room = ? ORDER BY m.id DESC LIMIT ?",
            (room, limit)
        )
    data = imlec.fetchall()
    conn.close()

    return data[::-1]
