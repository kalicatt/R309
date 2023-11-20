import socket
import threading
import mysql.connector
import bcrypt
import time

# Fonction pour établir une connexion à la base de données MySQL
def get_database_connection():
    try:
        return mysql.connector.connect(
            host="localhost",         # ou l'adresse de votre serveur de base de données
            user="chatuser", # l'utilisateur de la base de données
            password="root", # le mot de passe
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
shutdown_flag = threading.Event()

# Fonction pour envoyer des messages privés
def send_private_message(sender, message):
    if message.startswith("@"):
        parts = message.split(" ", 1)
        if len(parts) > 1 and parts[0][1:] in clients:
            destinataire = parts[0][1:]
            msg_to_send = f"Private from {sender}: {parts[1]}"
            clients[destinataire].send(msg_to_send.encode())
            return True
    return False

# Fonction pour diffuser les messages à tous les clients
# Correction dans la fonction broadcast
def broadcast(message, sender_username=None):
    print(f"Broadcasting message from {sender_username}: {message}")
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

    for username, sock in list(clients.items()):
        if username != sender_username:
            try:
                sock.send(message.encode())
            except Exception as e:
                print(f"Error sending message to {username}: {e}")
                sock.close()
                del clients[username]


# Fonction pour gérer chaque client connecté
# Correction dans la fonction handle_client
def handle_client(client_socket, client_address):
    try:
        # Recevoir le type de commande, le nom d'utilisateur et le mot de passe
        cmd_info = client_socket.recv(1024).decode()
        cmd, username, password = cmd_info.split(' ', 2)

        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if cmd == "REGISTER":
                if user:
                    client_socket.send(f"Username {username} is already taken. Please try a different username.".encode())
                    return
                else:
                    # Hacher le mot de passe avant de l'enregistrer
                    hashed_password = hash_password(password)
                    cursor.execute("INSERT INTO users (username, password, ip_address, last_login) VALUES (%s, %s, %s, NOW())",
                                   (username, hashed_password, str(client_address[0])))
                    conn.commit()
                    client_socket.send("Registration successful!".encode())

            elif cmd == "LOGIN":
                if user and verify_password(user[1], password):
                    client_socket.send("Login successful!".encode())
                else:
                    client_socket.send("Invalid login credentials.".encode())
                    return

            # Ajout du client à la liste des clients connectés
            clients[username] = client_socket
            broadcast(f"{username} has joined the chat.", sender_username=username)

            # Boucle pour gérer les messages entrants
            while True:
                message = client_socket.recv(1024).decode()
                if not message or message.lower() == 'bye':
                    broadcast(f"{username} has left the chat.", sender_username=username)
                    break

                if send_private_message(username, message):
                    continue

                broadcast(f"{username} says: {message}", sender_username=username)  

    except ConnectionResetError:
        pass
    except Exception as e:
        print(f"Error in handle_client: {e}")
    finally:
        client_socket.close()
        del clients[username]        



# Fonction pour les commandes du serveur
def server_command():
    while not shutdown_flag.is_set():
        cmd = input("")
        if cmd.lower() == 'arret':
            broadcast("Server is shutting down in 5 seconds...")
            time.sleep(5)
            shutdown_flag.set()
            broadcast("Server is now shutting down.")
            print("Server shutdown initiated.")
            for sock in clients.values():
                sock.close()
            break

# Fonction principale du serveur
def main():
    initialize_database()
    host = 'localhost'
    port = 50000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Server is listening on {host}:{port}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    except KeyboardInterrupt:
        print("Server is shutting down.")
    finally:
        server_socket.close()

if __name__ == '__main__':
    main()
