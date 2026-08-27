<p align="center">
  <img src="assets/logo.png" alt="ErkChat Logo" width="250"/>
</p>

# ErkChat Programme

ErkChat is a chat program built using Python's socket library.

I had no commercial motives while undertaking this project. I did it purely as a hobby and for personal use.
Also I code it because my purpose is learning socket programming.

## Features

### 1. Multiple users (clients) can connect.

### 2. Threading is used.

### 3. JSON protocol is used.

### 4. Special commands (users, msg, exit) are used.
>  /msg: Used for private messaging. 

Usage: /msg {USERNAME} {MESSAGE}

> /users: It lists online users.

> exit: It disconnects the user from the server.

> /nick: It changes your username.

Usage: /nick {NEW-USERNAME}

> /help: It shows all commands.

> /rooms: It shows all rooms.

> /room: It shows your current room.

> /join: It joins another room.

Usage: /join {NEW-ROOM}

> /whoami: It shows your username and role.

> /ping: It pings to the server and measures latency.
### 5. It has a SQLite database. You can register and login.

### 6. It has a room system. You can join a new room and chat to it.

### 7. It runs from the terminal (for now).

## Setup
To run the project on your own device, follow these steps:
### 1. Clone the repository.
```bash
git clone https://github.com/kotkukotku/erkchat.git
```
### 2. Navigate to the project directory.
```bash
cd erkchat
```
### 3. Start the server file through the first terminal. 
```bash
python server.py
```
### 4. Open the second terminal and start the client file by following steps 2 and 3. 
```bash
python client.py
```
## Note
This project is still under development. I make it for learning.
## Contributing
If you would like to contribute to the project, you can reach me at https://github.com/kotkukotku