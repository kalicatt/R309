import sys
import socket
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLineEdit, QInputDialog, 
                             QMessageBox, QListWidget, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal

class ClientThread(QThread):
    received_message = pyqtSignal(str)
    updated_user_list = pyqtSignal(list)

    def __init__(self, socket):
        super().__init__()
        self.socket = socket

    def run(self):
        while True:
            try:
                message = self.socket.recv(1024).decode()
                if message:
                    try:
                        data = json.loads(message)
                        if data["type"] == "user_list":
                            self.updated_user_list.emit(data["users"])
                    except json.JSONDecodeError:
                        self.received_message.emit(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_message(self, message):
        self.socket.send(message.encode())

    def stop(self):
        self.quit()
        self.wait()

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.socket = None
        self.current_room = None
        self.rooms = {}  # Dictionnaire pour stocker les onglets de chat des salons
        self.connect_to_server()

    def init_ui(self):
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)

        self.message_box = QLineEdit()
        self.message_box.returnPressed.connect(self.send_message)

        self.send_button = QPushButton('Envoyer')
        self.send_button.clicked.connect(self.send_message)

        self.user_list_widget = QListWidget(self)
        layout = QVBoxLayout()
        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_box)
        layout.addWidget(self.send_button)
        layout.addWidget(self.user_list_widget)

        self.setLayout(layout)
        self.setWindowTitle('Chat Client')
        self.resize(400, 300)

                # Ajout d'un widget pour sélectionner des salons
        self.room_select = QComboBox(self)
        self.room_select.addItem("Général")
        self.room_select.addItem("Blabla")
        self.room_select.addItem("Comptabilité")
        self.room_select.addItem("Informatique")
        self.room_select.addItem("Marketing")

        self.join_room_button = QPushButton('Rejoindre le salon', self)
        self.join_room_button.clicked.connect(self.join_room)

        self.leave_room_button = QPushButton('Quitter le salon', self)
        self.leave_room_button.clicked.connect(self.leave_room)

        # Ajout des boutons et du sélecteur de salon à la disposition
        room_layout = QHBoxLayout()
        room_layout.addWidget(self.room_select)
        room_layout.addWidget(self.join_room_button)
        room_layout.addWidget(self.leave_room_button)
        layout.addLayout(room_layout)

    def join_room(self):
        room_name = self.room_select.currentText()
        self.send_message(f"/join {room_name}")

    def leave_room(self):
        if self.current_room:
            self.send_message(f"/leave {self.current_room}")

    def update_user_list(self, user_list):
        self.user_list_widget.clear()
        for user in user_list:
            self.user_list_widget.addItem(user)

    def connect_to_server(self):
        server_ip, ok1 = QInputDialog.getText(self, 'Server IP', 'Enter server IP:', text='localhost')
        server_port, ok2 = QInputDialog.getInt(self, 'Server Port', 'Enter server port:', value=50000)
        
        if ok1 and ok2:
            self.socket = socket.socket()
            try:
                self.socket.connect((server_ip, server_port))
                self.authenticate_user()  # Séparation de la logique d'authentification
            except socket.error as e:
                QMessageBox.critical(self, "Connection Error", f"Unable to connect to the server: {e}")
                self.close()

    def authenticate_user(self):
        while True:
            choice, okPressed = QInputDialog.getItem(self, "Get item", "Login (L) or Register (R)?", ["Login", "Register"], 0, False)
            if okPressed and choice:
                username, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your username:')
                password, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your password:', QLineEdit.Password)
                if ok:
                    cmd = "REGISTER" if choice == "Register" else "LOGIN"
                    credentials = f"{cmd} {username} {password}"
                    self.socket.send(credentials.encode())

                    response = self.socket.recv(1024).decode()
                    if response == "Registration successful!" or response == "Login successful!":
                        self.client_thread = ClientThread(self.socket)
                        self.client_thread.received_message.connect(self.update_chat)
                        self.client_thread.updated_user_list.connect(self.update_user_list)
                        self.client_thread.start()
                        break
                    elif "banned" in response or "kicked" in response:
                        QMessageBox.warning(self, "Access Denied", response)
                        break
                    else:
                        QMessageBox.warning(self, "Warning", response)
                else:
                    break
            else:
                break

    
    def send_message(self, message=None):
        if message is None:
            message = self.message_box.text()
        self.message_box.clear()
        if message:
            self.update_chat(f"Moi: {message}")
            self.client_thread.send_message(message)


    def update_chat(self, message):
        # Gérer la mise à jour des onglets de chat pour différents salons
        if message.startswith("Vous avez rejoint le salon"):
            room_name = message.split(":")[1].strip()
            if room_name not in self.rooms:
                self.rooms[room_name] = QTextEdit()
                self.rooms[room_name].setReadOnly(True)
                self.tab_widget.addTab(self.rooms[room_name], room_name)
            self.current_room = room_name
        elif message.startswith("Vous avez quitté le salon"):
            room_name = message.split(":")[1].strip()
            if room_name in self.rooms:
                index = self.tab_widget.indexOf(self.rooms[room_name])
                self.tab_widget.removeTab(index)
                del self.rooms[room_name]
                self.current_room = None
        else:
            if self.current_room and self.current_room in self.rooms:
                self.rooms[self.current_room].append(message)
            else:
                self.chat_history.append(message)

    def closeEvent(self, event):
        if self.socket:
            self.client_thread.stop()
            self.socket.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    chat_window = ChatWindow()
    chat_window.show()
    sys.exit(app.exec_())
