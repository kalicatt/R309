import socket
import threading
import mysql.connector
import bcrypt
import time
import errno
import json

# Fonction pour établir une connexion à la base de données MySQL
def get_database_connection():
    try:
        return mysql.connector.connect(
            host="localhost",   # ou l'adresse de votre serveur de base de données
            user="chatuser",    # l'utilisateur de la base de données
            password="root",    # le mot de passe
            database="chat_server"    # le nom de la base de données
    )
    except mysql.connector.Error as e:
            print(f"Erreur de connexion à la base de données: {e}")
            return None

# Fonction pour initialiser la base de données et les tables
def initialize_database():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="chatuser",
            password="root"
        )
        cursor = conn.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS chat_server")
        cursor.execute("USE chat_server")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                ip_address VARCHAR(255),
                last_login DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                is_private BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_members (
                room_id INT,
                user_id INT,
                is_approved BOOLEAN NOT NULL DEFAULT FALSE,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)


        conn.commit()

    except mysql.connector.Error as e:
        print(f"Erreur lors de l'initialisation de la base de données: {e}")

    finally:
        if conn:
            cursor.close()
            conn.close()

# Fonction pour hacher un mot de passe
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Fonction pour vérifier un mot de passe haché
def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode(), stored_password.encode())

# Dictionnaire pour suivre les clients connectés
clients = {}

# Ensemble pour suivre les adresses IP bannies
banned_ips = set()

# Dictionnaire pour suivre les utilisateurs expulsés temporairement
kicked_users = {}  # username: timestamp de fin d'expulsion



shutdown_flag = threading.Event()

#definition des commandes serveur

def ban_user(ip_address):
    banned_ips.add(ip_address)

def unban_user(ip_address):
    banned_ips.discard(ip_address)

def kick_user(username, duration):
    kicked_users[username] = time.time() + duration

def unkick_user(username):
    del kicked_users[username]

def get_connected_users():
    return list(clients.keys())

def broadcast_user_list():
    connected_users = get_connected_users()
    for _, (client_socket, _) in clients.items():
        try:
            client_socket.send(json.dumps({"type": "user_list", "users": connected_users}).encode())
        except Exception as e:
            print(f"Error sending user list: {e}")


# Fonction pour envoyer des messages privés
def send_private_message(sender, message):
    if message.startswith("@"):
        parts = message.split(" ", 1)
        if len(parts) > 1 and parts[0][1:] in clients:
            destinataire = parts[0][1:]
            dest_socket, _ = clients[destinataire]  # Extraction du socket
            msg_to_send = f"Private from {sender}: {parts[1]}"
            dest_socket.send(msg_to_send.encode())
            return True
    return False


# Fonction pour diffuser les messages à tous les clients

def broadcast(message, sender_username=None):
    print(f"(Broadcasting message) {message}")
    sender_id = None
    with get_database_connection() as conn:
        cursor = conn.cursor()
        if sender_username:
            cursor.execute("SELECT id FROM users WHERE username = %s", (sender_username,))
            result = cursor.fetchone()
            if result:
                sender_id = result[0]
            cursor.execute("INSERT INTO messages (sender_id, message) VALUES (%s, %s)", (sender_id, message))
            conn.commit()

    for username, (client_socket, _) in clients.items():
        if username != sender_username:
            try:
                client_socket.send(message.encode())
            except Exception as e:
                print(f"Error sending message to {username}: {e}")
                client_socket.close()
                del clients[username]



# Fonction pour gérer chaque client connecté

def handle_client(client_socket, client_address):
    username = None  # Ajout pour capturer le nom d'utilisateur
    try:
        while not shutdown_flag.is_set():
            cmd_info = client_socket.recv(1024).decode()
            if not cmd_info:
                break

            cmd, username, password = cmd_info.split(' ', 2)

            with get_database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()

                if cmd == "REGISTER":
                    if user:
                        client_socket.send("Username is already taken. Please try a different username.".encode())
                        continue  # Permet à l'utilisateur de réessayer
                    else:
                        # Enregistrement de l'utilisateur
                        hashed_password = hash_password(password)
                        cursor.execute("INSERT INTO users (username, password, ip_address, last_login) VALUES (%s, %s, %s, NOW())",
                                       (username, hashed_password, str(client_address[0])))
                        conn.commit()
                        client_socket.send("Registration successful!".encode())
                        break  # Sortir de la boucle après un enregistrement réussi

                elif cmd == "LOGIN":
                    if user and verify_password(user[1], password):
                        # Vérifier si l'utilisateur est banni ou expulsé
                        if client_address[0] in banned_ips or (username in kicked_users and time.time() < kicked_users[username]):
                            client_socket.send("You are banned or kicked from the server.".encode())
                            client_socket.close()
                            continue  # Permet à l'utilisateur de réessayer

                        client_socket.send("Login successful!".encode())
                        break  # Sortir de la boucle après une connexion réussie
                    else:
                        client_socket.send("Invalid login credentials.".encode())
                        continue  # Permet à l'utilisateur de réessayer

        # Ajout du client à la liste des clients connectés et gestion des messages
        clients[username] = (client_socket, client_address[0])
        broadcast(f"{username} has joined the chat.", sender_username=username)
        broadcast_user_list()

        # Gestion des messages entrants
        while not shutdown_flag.is_set():
            message = client_socket.recv(1024).decode()
            if not message or message.lower() == 'bye':
                break

            if send_private_message(username, message):
                continue

            broadcast(f"{username} says: {message}", sender_username=username)

    except ConnectionResetError:
        print(f"Connection reset by peer: {client_address}")
    except socket.error as e:
        if e.errno == errno.WSAECONNABORTED:
            print(f"Connection aborted: {client_address}")
        else:
            print(f"Error in handle_client: {e}")
    except Exception as e:
        print(f"Error in handle_client: {e}")
    finally:
        # Fermeture du socket et suppression du client de la liste
        if username and username in clients:
            del clients[username]
            broadcast_user_list()
            if not shutdown_flag.is_set():
                broadcast(f"{username} has disconnected.")
        client_socket.close()

def fictiousclient():
    socketcli = socket.socket()
    socketcli.connect(('localhost', 50000))
    socketcli.close()

# Fonction pour les commandes du serveur
def server_command():
    global shutdown_flag
    while not shutdown_flag.is_set():
        cmd_input = input("Enter command: ")
        args = cmd_input.split()
        cmd = args[0].lower()

        if cmd == 'kill':
            broadcast("Server is shutting in 5 seconds...")
            time.sleep(5)
            broadcast("Server is shutting down now...")
            shutdown_flag.set()  # Déclenche l'arrêt du serveur
            # Fermer toutes les connexions clients
            for username, (client_socket, _) in clients.items():
                client_socket.close()
            break

        elif cmd == "ban":
            if len(args) < 2:
                print("Usage: ban <ip_address>")
            else:
                ban_user(args[1])
                # Fermer la connexion pour l'utilisateur banni
                for username, (client_socket, client_ip) in clients.items():
                    if client_ip == args[1]:
                        client_socket.close()
                        del clients[username]
                        break
                print(f"Server has banned IP address {args[1]}")

        elif cmd == "unban":
            if len(args) < 2:
                print("Usage: unban <ip_address>")
            else:
                unban_user(args[1])
                print(f"Server has unbanned IP address {args[1]}")

        elif cmd == "kick":
            if len(args) < 3:
                print("Usage: kick <username> <duration_in_seconds>")
            else:
                kick_user(args[1], int(args[2]))
                # Fermer la connexion pour l'utilisateur expulsé
                if args[1] in clients:
                    clients[args[1]][0].close()
                    del clients[args[1]]
                print(f"Server has kicked user {args[1]} for {args[2]} seconds")

        elif cmd == "unkick":
            if len(args) < 2:
                print("Usage: unkick <username>")
            else:
                unkick_user(args[1])
                print(f"Server has unkicked user {args[1]}")



# Fonction principale du serveur
def main():
    initialize_database()
    host = 'localhost'
    port = 50000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Server is listening on {host}:{port}")

    # Thread pour accepter les connexions clients
    def accept_clients(server_socket):
        try:
            while not shutdown_flag.is_set():
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")
                if not shutdown_flag.is_set():
                    client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address),daemon=True)
                    client_thread.start()
        except Exception as e:
            print(f"Error accepting clients: {e}")

    client_accept_thread = threading.Thread(target=accept_clients, args=(server_socket,))
    client_accept_thread.start()

    # Thread pour les commandes du serveur
    command_thread = threading.Thread(target=server_command, daemon=True)
    command_thread.start()

    # Attendre que les threads se terminent proprement
    client_accept_thread.join()
    command_thread.join()

    # Fermer tous les sockets clients
    for _, (client_socket, _) in clients.items():
        client_socket.close()

    # Fermer le socket serveur
    server_socket.close()
    print("Server has been shut down.")

if __name__ == '__main__':
    main()

