import socket

client_socket = socket.socket()
client_socket.connect(('localhost', 50000))

message = input('Enter your message: ')
client_socket.send(message.encode())

reply = client_socket.recv(1024).decode()
print(f'Received reply: {reply}')

client_socket.close()