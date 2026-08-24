from protocol import send_json
import database

DEFAULT_ROOM = "lobby"
def send_room_history(conn, room_name):
    old_messages = database.get_last_messages(limit=15, room=room_name)
    if old_messages:
        send_json(conn, {
            "type": "system",
            "text": f"\n-- #{room_name} GEÇMİŞ MESAJLARI --"
        })
        for sender, message, receiver, saat, room in old_messages:
            send_json(conn, {
                "type": "chat",
                "text": f"[{saat}] [{room}] {sender}: {message}"
            })
        send_json(conn, {
            "type": "system",
            "text": "--------------------------------\n"
        })

def handle_nick(conn, new_name, nicknames, lock, broadcast):
    old_nickname = nicknames.get(conn)
    new_user = new_name.strip()
    with lock:
        nick_taken = new_user in nicknames.values()
    if not new_user:
        send_json(conn, {
            "type": "system",
            "text": "Kullanıcı ismi boş olamaz.\n",
        })
        return
    if nick_taken:
        send_json(conn, {
            "type":"system",
            "text": "Bu kullanıcı adı şu an aktif birinde zaten var.\n"
        })
        return
    elif old_nickname == new_user:
        send_json(conn, {
            "type": "system",
            "text": "Lütfen farklı bir kullanıcı adı girin.\n",
        })
        return
    else:
        if database.update_username(old_nickname, new_user):
            with lock:
                nicknames[conn] = new_user
            new_msg = f"{old_nickname} ismini {new_user} olarak değiştirdi."
            send_json(conn, {
                "type": "system",
                "text": "İsminiz değiştirildi.\n",
            })
            broadcast({
                "type": "system",
                "text": new_msg,
            }, conn)
            return
        else:
            send_json(conn,{"type":"system",
            "text":"Bu kullanıcı adı veritabanında kayıtlı.\n"})
def handle_users(conn, nicknames, lock, rooms=None, client_rooms=None):
    with lock:
        if rooms is None or client_rooms is None:
            user_list = "\n".join(nicknames.values())
            title = "Online users"
        else:
            room_name = client_rooms.get(conn, DEFAULT_ROOM)
            room_clients = rooms.get(room_name, set())
            user_list = "\n".join(
                nicknames.get(client, "Unknown") for client in room_clients
            )
            title = f"Online users in #{room_name}"
        users_msg = {
            "type": "system",
            "text": f"{title}:\n{user_list}\n",
        }
    send_json(conn,users_msg)

def handle_rooms(conn, rooms, client_rooms, lock):
    with lock:
        current_room = client_rooms.get(conn, DEFAULT_ROOM)
        room_lines = []
        for room_name in sorted(rooms):
            marker = "*" if room_name == current_room else " "
            user_count = len(rooms[room_name])
            room_lines.append(f"{marker} #{room_name} ({user_count})")

    send_json(conn, {
        "type": "system",
        "text": "Odalar:\n" + "\n".join(room_lines) + "\n",
    })

def handle_join(conn, room_name, nicknames, rooms, client_rooms, lock, broadcast_room):
    new_room = room_name.strip()

    if not new_room:
        send_json(conn, {
            "type": "system",
            "text": "Oda adı boş olamaz.\n",
        })
        return

    if " " in new_room or len(new_room) > 30:
        send_json(conn, {
            "type": "system",
            "text": "Oda adı boşluk içeremez ve 30 karakterden uzun olamaz.\n",
        })
        return

    with lock:
        username = nicknames.get(conn, "Unknown")
        old_room = client_rooms.get(conn, DEFAULT_ROOM)

        if old_room == new_room:
            send_json(conn, {
                "type": "system",
                "text": f"Zaten #{new_room} odasındasınız.\n",
            })
            return

        database.add_room(new_room)
        if old_room in rooms:
            rooms[old_room].discard(conn)
            if old_room != DEFAULT_ROOM and not rooms[old_room]:
                rooms.pop(old_room, None)

        rooms.setdefault(new_room, set()).add(conn)
        client_rooms[conn] = new_room

    broadcast_room(old_room, {
        "type": "system",
        "text": f"{username} #{old_room} odasından ayrıldı.",
    }, conn)
    broadcast_room(new_room, {
        "type": "system",
        "text": f"{username} #{new_room} odasına katıldı.",
    }, conn)
    send_json(conn, {
        "type": "system",
        "text": f"#{new_room} odasına geçtiniz.\n",
    })

    send_room_history(conn, new_room)
def handle_room(conn, client_rooms, lock):
    with lock:
        room_name = client_rooms.get(conn, DEFAULT_ROOM)

    send_json(conn, {
        "type": "system",
        "text": f"Şu an #{room_name} odasındasınız.\n",
    })


def handle_leave(conn, nicknames, rooms, client_rooms, lock, broadcast_room):
    with lock:
        username = nicknames.get(conn, "Unknown")
        old_room = client_rooms.get(conn, DEFAULT_ROOM)

        if old_room == DEFAULT_ROOM:
            send_json(conn, {
                "type": "system",
                "text": "Zaten lobby odasındasınız.\n",
            })
            return

        if old_room in rooms:
            rooms[old_room].discard(conn)
            if not rooms[old_room]:
                rooms.pop(old_room, None)

        rooms.setdefault(DEFAULT_ROOM, set()).add(conn)
        client_rooms[conn] = DEFAULT_ROOM

    broadcast_room(old_room, {
        "type": "system",
        "text": f"{username} #{old_room} odasından ayrıldı.",
    }, conn)

    broadcast_room(DEFAULT_ROOM, {
        "type": "system",
        "text": f"{username} #{DEFAULT_ROOM} odasına katıldı.",
    }, conn)

    send_json(conn, {
        "type": "system",
        "text": f"#{DEFAULT_ROOM} odasına döndünüz.\n",
    })
    send_room_history(conn, DEFAULT_ROOM)
def handle_help(conn):
    help_text = (
        "\nKomutlar:\n"
        "/users: Bulunduğun odadaki online kullanıcılar\n"
        "/rooms: Odaları listeler\n"
        "/join (oda): Odaya katılır, yoksa oluşturur\n"
        "/room: Bulunduğun odayı gösterir\n"
        "/leave: Bulunduğun odadan çıkıp lobby'ye döner\n"
        "/nick (isim): İsim değiştirir\n"
        "/msg (user) (mesaj): DM'den mesaj atar\n"
        "/whoami: Kullanıcı adı ve rolü gösterir.\n"
        "/ping: Sunucuya ping atıp gecikmeyi ölçer.\n"
        "exit: Çıkış\n"
    )
    send_json(conn, {
        "type": "system",
        "text": help_text,
    })
def handle_whoami(conn,nicknames,role):
    text = f"Kullanıcı adı: {nicknames.get(conn,'Unknown')}\nRol: {role}\n"
    send_json(conn, {
        "type": "system",
        "text": text
    })
