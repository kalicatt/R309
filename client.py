import socket
import threading
import sys

# Flag de fermeture pour indiquer aux threads de s'arrêter
close_flag = threading.Event()

def send_messages(server_socket):
    while not close_flag.is_set():
        try:
            message = input("Enter your message: ")
            if message.lower() == 'bye':
                close_flag.set()
                server_socket.send(message.encode())
                break
            else:
                server_socket.send(message.encode())
        except BrokenPipeError:
            break

def receive_messages(server_socket):
    while not close_flag.is_set():
        try:
            message = server_socket.recv(1024).decode()
            if message:
                print(f"\n{message}")
            else:
                # Si aucun message n'est reçu, cela signifie que le serveur a fermé la connexion.
                close_flag.set()
                break
        except ConnectionResetError:
            # Si le serveur se ferme brusquement, un ConnectionResetError sera levé.
            print("\nServer disconnected abruptly")
            close_flag.set()
            break

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket()
    server_socket.connect((host, port))

    # Threads pour gérer l'envoi et la réception des messages
    send_thread = threading.Thread(target=send_messages, args=(server_socket,))
    receive_thread = threading.Thread(target=receive_messages, args=(server_socket,))

    receive_thread.start()
    send_thread.start()

    # Attendre que les threads se terminent proprement
    send_thread.join()
    receive_thread.join()

    print("Disconnected from the chat server.")
    server_socket.close()

if __name__ == '__main__':
    main()
