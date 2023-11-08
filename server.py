import socket
import sys

def main():
    host = 'localhost'
    port = 50000

    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f'Server is listening on {host}:{port}')

    while True:
        client_socket, client_address = server_socket.accept()
        print(f'Connection from {client_address}')

        message = client_socket.recv(1024).decode()
        print(f'Message: {message}')

        if message == 'arret':
            client_socket.send('Server will be shutdown'.encode())
            server_socket.close()
            sys.exit()
        elif message == 'bye':
            client_socket.send('Client will be disconnected'.encode())
            client_socket.close()
        

        client_socket.close()

if __name__ == '__main__':
    main()