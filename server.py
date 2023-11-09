import socket
import sys
import threading

# Flag pour indiquer à tous les threads de se terminer
shutdown_flag = threading.Event()

def send_messages(client_socket):
    while not shutdown_flag.is_set():
        try:
            server_message = input("Enter your message to client: ")
            if server_message.lower() == "arret":
                shutdown_flag.set()
                print("Server will be shutdown")
                client_socket.send("Server will be shutdown".encode())
                client_socket.close()
                break
            else:
                client_socket.send(server_message.encode())
        except BrokenPipeError:
            break  # Si le client ferme la connexion

def receive_messages(client_socket):
    while not shutdown_flag.is_set():
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            print(f"Client says: {message}")
            if message.lower() == "bye":
                print("Client will be disconnected")
                client_socket.send("Client will be disconnected".encode())
                break
        except ConnectionResetError:
            print("Client disconnected abruptly")
            break

def handle_client(client_socket):
    send_thread = threading.Thread(target=send_messages, args=(client_socket,))
    send_thread.start()
    receive_messages(client_socket)
    send_thread.join()

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server is listening on {host}:{port}")

    try:
        while not shutdown_flag.is_set():
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.start()
    except KeyboardInterrupt:
        print("Server is shutting down due to keyboard interrupt.")
        shutdown_flag.set()
    finally:
        server_socket.close()
        sys.exit()

if __name__ == '__main__':
    main()
