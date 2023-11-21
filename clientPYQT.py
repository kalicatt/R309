import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, QInputDialog, QMessageBox, QListWidget
from PyQt5.QtCore import QThread, pyqtSignal
import socket
import json

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
                        else:
                            self.received_message.emit(message)
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
        self.socket = socket.socket()
        self.is_connected = False
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

    def update_user_list(self, user_list):
        self.user_list_widget.clear()
        for user in user_list:
            self.user_list_widget.addItem(user)

    def connect_to_server(self):
        while not self.is_connected:
            choice, okPressed = QInputDialog.getItem(self, "Get item", "Login (L) or Register (R)?", ["Login", "Register"], 0, False)
            if okPressed and choice:
                username, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your username:')
                password, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your password:', QLineEdit.Password)
                if ok:
                    try:
                        self.socket.connect(('localhost', 50000))
                        cmd = "REGISTER" if choice == "Register" else "LOGIN"
                        credentials = f"{cmd} {username} {password}"
                        self.socket.send(credentials.encode())

                        response = self.socket.recv(1024).decode()
                        if response == "Registration successful!" or response == "Login successful!":
                            self.client_thread = ClientThread(self.socket)
                            self.client_thread.received_message.connect(self.update_chat)
                            self.client_thread.updated_user_list.connect(self.update_user_list)
                            self.client_thread.start()
                            self.is_connected = True
                        elif "banned" in response or "kicked" in response:
                            QMessageBox.warning(self, "Access Denied", response)
                            break
                        else:
                            QMessageBox.warning(self, "Warning", response)
                    except socket.error as e:
                        QMessageBox.critical(self, "Connection Error", f"Unable to connect to the server: {e}")
                        break
            else:
                break

    def send_message(self):
        message = self.message_box.text()
        self.message_box.clear()
        if message:
            self.update_chat(f"Moi: {message}")
            self.client_thread.send_message(message)

    def update_chat(self, message):
        self.chat_history.append(message)

    def closeEvent(self, event):
        if self.is_connected:
            self.client_thread.stop()
            self.socket.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    chat_window = ChatWindow()
    chat_window.show()
    sys.exit(app.exec_())
