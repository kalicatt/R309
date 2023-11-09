import socket
import threading
import sys

# Ce dictionnaire gardera une trace des connexions clients.
clients = {}
shutdown_flag = threading.Event()

def broadcast(message, exclude_address=None):
    for other_client, sock in list(clients.items()):
        if other_client != exclude_address:
            try:
                sock.send(message.encode())
            except Exception as e:
                print(f"Error sending message to {other_client}: {e}")

def handle_client(client_socket, client_address):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message or message.lower() == 'bye':
                # Informer les autres clients que ce client s'est déconnecté
                broadcast(f"{client_address} has disconnected from the chat.", exclude_address=client_address)
                break

            # Afficher le message sur le serveur
            print(f"{client_address} says: {message}")
            
            # Renvoyer le message à tous les autres clients
            broadcast(f"{client_address} says: {message}", exclude_address=client_address)

        except ConnectionResetError:
            break
        except Exception as e:
            print(f"Error: {e}")
            break

    # Lorsqu'un client se déconnecte
    print(f"Client {client_address} has disconnected.")
    client_socket.close()
    del clients[client_address]

def server_command():
    while not shutdown_flag.is_set():
        cmd = input("")
        if cmd.lower() == 'arret':
            shutdown_flag.set()
            broadcast("Server is shutting down now!")
            print("Server shutdown initiated.")
            for client_socket in clients.values():
                client_socket.close()
            sys.exit()

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"Server is listening on {host}:{port}")

    # Start the server command thread
    server_command_thread = threading.Thread(target=server_command)
    server_command_thread.start()

    try:
        while not shutdown_flag.is_set():
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            # Ajouter le client à la liste des clients
            clients[client_address] = client_socket

            # Démarrer un nouveau thread pour gérer la connexion
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
