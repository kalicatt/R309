import socket
import threading
import sys

# Ce dictionnaire gardera une trace des noms d'utilisateurs et des connexions clients.
clients = {}
shutdown_flag = threading.Event()

def send_private_message(sender, message):
    # Format du message privé: "@destinataire message"
    if message.startswith("@"):
        parts = message.split(" ", 1)
        if len(parts) > 1 and parts[0][1:] in clients:
            destinataire = parts[0][1:]
            msg_to_send = f"Private from {sender}: {parts[1]}"
            clients[destinataire].send(msg_to_send.encode())
            return True
    return False

def broadcast(message, exclude_address=None):
    for username, sock in list(clients.items()):
        if username != exclude_address:
            try:
                sock.send(message.encode())
            except Exception as e:
                print(f"Error sending message to {username}: {e}")

def handle_client(client_socket, client_address):
    client_socket.send("Enter your username: ".encode())
    username = client_socket.recv(1024).decode().strip()

    if username in clients:
        client_socket.send(f"Username {username} is already taken. Please reconnect with a different username.".encode())
        client_socket.close()
        return

    clients[username] = client_socket
    broadcast(f"{username} has joined the chat.", exclude_address=username)

    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message or message.lower() == 'bye':
                broadcast(f"{username} has left the chat.", exclude_address=username)
                break

            if send_private_message(username, message):
                continue  # Si c'était un message privé, ne pas l'envoyer à tout le monde

            broadcast(f"{username} says: {message}", exclude_address=username)

        except ConnectionResetError:
            break
        except Exception as e:
            print(f"Error: {e}")
            break

    print(f"Client {username} has disconnected.")
    client_socket.close()
    del clients[username]

def server_command():
    while not shutdown_flag.is_set():
        cmd = input("")
        if cmd.lower() == 'arret':
            shutdown_flag.set()
            broadcast("Server is shutting down now!")
            print("Server shutdown initiated.")
            for sock in clients.values():
                sock.close()
            break

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"Server is listening on {host}:{port}")

    server_command_thread = threading.Thread(target=server_command)
    server_command_thread.start()

    try:
        while not shutdown_flag.is_set():
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()

    except KeyboardInterrupt:
        print("Server is shutting down due to keyboard interrupt.")
        shutdown_flag.set()
    finally:
        server_socket.close()
        sys.exit()

if __name__ == '__main__':
    main()
