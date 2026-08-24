#server.py

import socket
import threading
import json

import database
import auth
import messages
import commands
from protocol import send_json

lock = threading.Lock()
database.init_db()

ip = "0.0.0.0"
port = 4444
clients = []
nicknames = {}
user_ids = {}
rooms = {room_name: set() for room_name in database.get_room_names()}
client_rooms = {}
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((ip, port))
s.listen()

def broadcast_room(room_name, new_msg, sender_client=None):
    with lock:
        current_clients = list(rooms.get(room_name, set()))

    for client in current_clients:
        if sender_client == client:
            continue

        if not send_json(client, new_msg):
            reseting(client)

def get_nickname(conn):
    with lock:
        return nicknames.get(conn, "Unknown")

def get_room(conn):
    with lock:
        return client_rooms.get(conn, "lobby")
    
def broadcast(new_msg, sender_client):
    with lock:
        current_clients = clients.copy()
    for client in current_clients:
        if sender_client == client:
            continue

        if not send_json(client, new_msg):
            reseting(client)


def reseting(conn):
    with lock:
        try:
            clients.remove(conn)
        except ValueError:
            pass

        room_name = client_rooms.pop(conn, None)
        if room_name in rooms:
            rooms[room_name].discard(conn)

        nicknames.pop(conn, None)
        user_ids.pop(conn, None)
    try:
        conn.close()
    except:
        pass


def receive(conn, addr):
    f = conn.makefile("r", encoding="utf-8", errors="ignore")
    current_nick, user_id, user_role = auth.handle_client_auth(
        conn,
        f,
        nicknames,
        lock,
        broadcast
    )

    if current_nick is None:
        reseting(conn)
        return
    with lock:
        clients.append(conn)
        user_ids[conn] = user_id

        default_room = "lobby"
        rooms.setdefault(default_room, set()).add(conn)
        client_rooms[conn] = default_room
    broadcast_room(default_room, {
    "type": "system",
    "text": f"{current_nick} bağlandı."
    }, conn)       
    
    commands.send_room_history(conn, default_room)
    while True:
        try:
            raw = f.readline().strip()
        except (ConnectionResetError, ConnectionError, OSError):
            raw = None
        
        if not raw:
            nickname = get_nickname(conn)
            room_name = get_room(conn)
            reseting(conn)
            if nickname:
                broadcast_room(room_name, {
                    "type": "system",
                    "text": f"{nickname} ayrıldı.",
                }, conn)
            break

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "msg":
            room_name = get_room(conn)
            messages.handle_message(
                conn,
                data["text"],
                nicknames,
                user_ids,
                lock,
                broadcast_room,
                room_name
            )
            continue

        if data.get("type") == "exit":
            nickname = get_nickname(conn)
            room_name = get_room(conn)
            broadcast_room(room_name, {
                "type": "system",
                "text": f"{nickname} ayrıldı.",
            }, conn)
            shut_msg = {
                "type": "system",
                "event": "shutdown",
                "text": "Başarıyla çıkış yapıldı.",
            }
            send_json(conn, shut_msg)
            reseting(conn)
            break

        if data.get("type") == "command" and data.get("name") == "users":
            commands.handle_users(conn,nicknames,lock,rooms,client_rooms)
            continue

        if data.get("type") == "command" and data.get("name") == "rooms":
            commands.handle_rooms(conn, rooms, client_rooms, lock)
            continue

        if data.get("type") == "command" and data.get("name") == "join":
            commands.handle_join(
                conn,
                data.get("room",""),
                nicknames,
                rooms,
                client_rooms,
                lock,
                broadcast_room
            )
            continue
        if data.get("type") == "command" and data.get("name") == "room":
            commands.handle_room(conn, client_rooms, lock)
            continue

        if data.get("type") == "command" and data.get("name") == "leave":
            commands.handle_leave(
                conn,
                nicknames,
                rooms,
                client_rooms,
                lock,
                broadcast_room
            )
            continue
        if data.get("type") == "nick":
            room_name = get_room(conn)
            commands.handle_nick(
                conn,
                data.get("new_name",""),
                nicknames,
                lock,
                lambda msg, sender: broadcast_room(room_name, msg, sender))    
            continue
        if data.get("type") == "command" and data.get("name") == "help":
            commands.handle_help(conn)
            continue
        if data.get("type") == "command" and data.get("name") == "ping":
            send_json(conn,{
                "type": "ping_response",
                "time": data.get("time")
            })
            continue
        if data.get("type") == "command" and data.get("name") == "whoami":
            commands.handle_whoami(conn,nicknames,user_role)
            continue
        if data.get("type") == "dm":
            messages.handle_dm(
                conn,
                data.get("to"),
                data.get("text",""),
                nicknames,
                user_ids,
                lock,
                get_nickname
            )
            continue


print(f"Server {port} portunda başlatıldı. Kapatmak için Ctrl+C yapın.")
try:
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=receive, args=(conn, addr), daemon=True).start()
        except OSError:
            break
except KeyboardInterrupt:
    print("\nCtrl+C algılandı. Server kapatılıyor.")
finally:
    print("Bağlantılar sonlandırılıyor...")
    with lock:
        current_clients = clients.copy()
    for client in current_clients:
        try:
            send_json(client, {
                "type": "system",
                "event": "shutdown",
                "text": "Server kapatıldı.",
            })
            reseting(client)
        except Exception as e:
            print("Hata oluştu:", e)
    s.close()
    print("Server güvenli şekilde kapatıldı.")
