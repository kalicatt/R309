import socket

client_socket = socket.socket()
client_socket.connect(('localhost', 50000))

message = input('Enter your message: ')
client_socket.send(message.encode())



client_socket.close()