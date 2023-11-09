import socket
import threading

def send_messages(server_socket):
    while True:
        message = input("Enter your message: ")
        server_socket.send(message.encode())
        if message.lower() == 'bye':
            break

def receive_messages(server_socket):
    while True:
        try:
            message = server_socket.recv(1024).decode()
            print(f"Server says: {message}")
            if message.lower() == "server will be shutdown":
                print("Server has been shutdown. Exiting.")
                break
        except ConnectionResetError:
            print("Server disconnected abruptly")
            break

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket()
    server_socket.connect((host, port))

    # Threads pour gérer l'envoi et la réception des messages
    send_thread = threading.Thread(target=send_messages, args=(server_socket,))
    receive_thread = threading.Thread(target=receive_messages, args=(server_socket,))

    send_thread.start()
    receive_thread.start()

    send_thread.join()
    receive_thread.join()

    server_socket.close()

if __name__ == '__main__':
    main()
