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

        # Créer la base de données si elle n'existe pas
        cursor.execute("CREATE DATABASE IF NOT EXISTS chat_server")
        cursor.execute("USE chat_server")

        # Créer les tables si elles n'existent pas
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
                FOREIGN KEY (user_id) REFERENCES users(id),
                PRIMARY KEY (room_id, user_id)
            )
        """)

        # Insérer les salons par défaut
        default_rooms = [
            ('Général', False),
            ('Blabla', False),
            ('Comptabilité', True),
            ('Informatique', True),
            ('Marketing', True)
        ]

        for room_name, is_private in default_rooms:
            cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_name,))
            room = cursor.fetchone()
            if not room:
                cursor.execute("INSERT INTO rooms (name, is_private) VALUES (%s, %s)", (room_name, is_private))

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


def add_admin_user():
    print("Tentative d'ajout de l'administrateur...")
    admin_username = "admin"
    admin_password = "admin"  # Remplacez par un mot de passe sécurisé

    # Hacher le mot de passe
    hashed_password = hash_password(admin_password)

    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        # Vérifier si l'administrateur existe déjà
        cursor.execute("SELECT id FROM users WHERE username = %s", (admin_username,))
        if cursor.fetchone():
            print("Un administrateur existe déjà.")
        else:
            # Insérer l'administrateur car il n'existe pas encore
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                           (admin_username, hashed_password))
            conn.commit()
            print("Administrateur ajouté avec succès.")
            
    except mysql.connector.Error as e:
        print(f"Erreur lors de l'ajout de l'administrateur: {e}")

    finally:
        cursor.close()
        conn.close()


def join_room(cursor, username, room_name):
    # Recherchez l'ID de l'utilisateur
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cursor.fetchone()[0]
    
    # Recherchez l'ID du salon
    cursor.execute("SELECT id, is_private FROM rooms WHERE name = %s", (room_name,))
    room = cursor.fetchone()
    
    if room:
        room_id, is_private = room
        # Vérifiez si l'utilisateur est déjà membre du salon
        cursor.execute("SELECT * FROM room_members WHERE room_id = %s AND user_id = %s", (room_id, user_id))
        if cursor.fetchone():
            return "You are already a member of this room."
        
        # Si le salon est privé, l'utilisateur doit être approuvé
        if is_private:
            cursor.execute("INSERT INTO room_members (room_id, user_id, is_approved) VALUES (%s, %s, FALSE)", (room_id, user_id))
            return "Request to join the room has been sent and is pending approval."
        else:
            cursor.execute("INSERT INTO room_members (room_id, user_id, is_approved) VALUES (%s, %s, TRUE)", (room_id, user_id))
            return "You have joined the room."
    else:
        return "Room does not exist."

def leave_room(cursor, username, room_name):
    # Recherchez l'ID de l'utilisateur
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cursor.fetchone()[0]
    
    # Recherchez l'ID du salon
    cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_name,))
    room = cursor.fetchone()
    
    if room:
        room_id = room[0]
        cursor.execute("DELETE FROM room_members WHERE room_id = %s AND user_id = %s", (room_id, user_id))
        return "You have left the room."
    else:
        return "Room does not exist."

def send_room_message(cursor, username, room_name, message):
    # Recherchez l'ID de l'utilisateur
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cursor.fetchone()[0]
    
    # Recherchez l'ID du salon
    cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_name,))
    room = cursor.fetchone()
    
    if room:
        room_id = room[0]
        # Vérifiez si l'utilisateur est membre du salon et approuvé
        cursor.execute("SELECT * FROM room_members WHERE room_id = %s AND user_id = %s AND is_approved = TRUE", (room_id, user_id))
        if cursor.fetchone():
            # Insérez le message dans la table des messages
            cursor.execute("INSERT INTO messages (sender_id, message, room_id) VALUES (%s, %s, %s)", (user_id, message, room_id))

            # Formatage du message pour inclure le nom de l'utilisateur et le salon
            formatted_message = f"{username} in {room_name}: {message}"

            # Envoyez le message formaté uniquement aux membres du salon spécifié
            broadcast_to_room(room_name, formatted_message, sender_username=username)
            return "Message sent successfully."
        else:
            return "You are not a member of this room or your request has not been approved yet."
    else:
        return "Room does not exist."



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

def broadcast_to_room(room_name, message, sender_username=None):
    with get_database_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM room_members WHERE room_id = (SELECT id FROM rooms WHERE name = %s)", (room_name,))
        member_ids = [row[0] for row in cursor.fetchall()]
        for member_id in member_ids:
            for username, (client_socket, _) in clients.items():
                if username != sender_username:
                    try:
                        client_socket.send(message.encode())
                    except Exception as e:
                        print(f"Error sending message to {username}: {e}")
                        client_socket.close()
                        del clients[username]

def show_pending_requests(cursor):
    cursor.execute("""
        SELECT users.username, rooms.name
        FROM room_members
        JOIN users ON room_members.user_id = users.id
        JOIN rooms ON room_members.room_id = rooms.id
        WHERE is_approved = FALSE
    """)
    pending_requests = cursor.fetchall()
    for request in pending_requests:
        print(f"Utilisateur: {request[0]}, Salon: {request[1]}")


def handle_room_requests(cursor, admin_decision, username, room_name):
    # Décider de l'action à entreprendre
    is_approved = True if admin_decision.lower() == 'approve' else False

    # Mise à jour de la demande d'inscription
    cursor.execute("""
        UPDATE room_members
        SET is_approved = %s
        WHERE user_id = (SELECT id FROM users WHERE username = %s)
        AND room_id = (SELECT id FROM rooms WHERE name = %s)
    """, (is_approved, username, room_name))





# Fonction pour gérer chaque client connecté

def handle_client(client_socket, client_address):
    username = None
    try:
        # Établir la connexion avec la base de données
        with get_database_connection() as conn:
            cursor = conn.cursor()

            # Boucle principale pour gérer les commandes du client
            while not shutdown_flag.is_set():
                cmd_info = client_socket.recv(1024).decode()
                if not cmd_info:
                    break

                cmd, username, password = cmd_info.split(' ', 2)

                # Traitement des commandes REGISTER et LOGIN
                if cmd == "REGISTER":
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cursor.fetchone():
                        client_socket.send("Username is already taken. Please try a different username.".encode())
                        continue
                    else:
                        hashed_password = hash_password(password)
                        cursor.execute("INSERT INTO users (username, password, ip_address, last_login) VALUES (%s, %s, %s, NOW())",
                                       (username, hashed_password, str(client_address[0])))
                        conn.commit()
                        client_socket.send("Registration successful!".encode())
                        break

                elif cmd == "LOGIN":
                    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    if user and verify_password(user[1], password):
                        client_socket.send("Login successful!".encode())
                        
                         # Vérifier si l'utilisateur est l'administrateur
                        if username == "admin":
                            # Vous êtes maintenant connecté en tant qu'administrateur
                            # Vous pouvez ajouter ici des logiques spécifiques à l'administrateur
                            client_socket.send("Logged in as administrator.".encode())
                            break
                    else:
                        client_socket.send("Invalid login credentials.".encode())
                        continue

            # Ajouter le client à la liste des clients connectés
            clients[username] = (client_socket, client_address[0])
            broadcast(f"{username} has joined the chat.", sender_username=username)
            broadcast_user_list()

            # Gestion des messages entrants
            while not shutdown_flag.is_set():
                message = client_socket.recv(1024).decode()

                if message.startswith('/join'):
                    _, room_name = message.split()
                    response = join_room(cursor, username, room_name)
                    client_socket.send(response.encode())

                elif message.startswith('/leave'):
                    _, room_name = message.split()
                    response = leave_room(cursor, username, room_name)
                    client_socket.send(response.encode())

                elif message.startswith('/msg'):
                    _, room_name, room_message = message.split(' ', 2)
                    response = send_room_message(cursor, username, room_name, room_message)
                    client_socket.send(response.encode())

                elif message.startswith("@"):
                    # Logique pour les messages privés
                    if send_private_message(username, message):
                        continue

                else:
                    # Logique pour les messages publics
                    broadcast(f"{username} says: {message}", sender_username=username)

    except ConnectionResetError:
        print(f"Connection reset by peer: {client_address}")
    except socket.error as e:
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
    admin_authenticated = False

    # Authentifier l'administrateur
    while not admin_authenticated:
        print("Veuillez vous connecter pour accéder aux commandes serveur.")
        admin_username = input("Nom d'utilisateur administrateur : ")
        admin_password = input("Mot de passe administrateur : ")

        # Vérifiez les identifiants avec la base de données
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = %s", (admin_username,))
            result = cursor.fetchone()
            if result and verify_password(result[0], admin_password):
                admin_authenticated = True
                print("Connecté en tant qu'administrateur. Vous pouvez exécuter des commandes serveur.")
            else:
                print("Identifiants incorrects. Veuillez réessayer.")

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

        elif cmd == "show_requests":
            with get_database_connection() as conn:
                cursor = conn.cursor()
                show_pending_requests(cursor)

        elif cmd == "handle_request":
            if len(args) < 4:
                print("Usage: handle_request <approve/reject> <username> <room_name>")
            else:
                with get_database_connection() as conn:
                    cursor = conn.cursor()
                    handle_room_requests(cursor, args[1], args[2], args[3])
                    conn.commit()


# Fonction principale du serveur
def main():
    initialize_database()
    add_admin_user()
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