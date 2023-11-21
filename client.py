import socket
import threading
import json

def receive_messages(sock):
    while True:
        try:
            message = sock.recv(1024).decode()
            if message:
                try:
                    data = json.loads(message)
                    if data["type"] == "user_list":
                        print("Utilisateurs connectés :", ', '.join(data["users"]))
                    else:
                        print(message)
                except json.JSONDecodeError:
                    print(message)
        except Exception as e:
            print(f"Erreur lors de la réception du message : {e}")
            break

def main():
    host = 'localhost'
    port = 50000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
    except Exception as e:
        print(f"Impossible de se connecter au serveur : {e}")
        return

    choice = input("Login (L) or Register (R)? ").strip().lower()
    username = input("Entrez votre nom d'utilisateur : ").strip()
    password = input("Entrez votre mot de passe : ").strip()

    cmd = "REGISTER" if choice == 'r' else "LOGIN"
    credentials = f"{cmd} {username} {password}"
    sock.send(credentials.encode())

    response = sock.recv(1024).decode()
    print(response)

    if "successful" not in response:
        sock.close()
        return

    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    while True:
        message = input()
        if message.lower() == 'quit':
            break
        sock.send(message.encode())

    sock.close()

if __name__ == "__main__":
    main()
