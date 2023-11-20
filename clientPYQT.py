import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, QInputDialog
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor
import socket

class ClientThread(QThread):
    received_message = pyqtSignal(str)

    def __init__(self, socket):
        super().__init__()
        self.socket = socket

    def run(self):
        while True:
            try:
                message = self.socket.recv(1024).decode()
                print(f"Message received: {message}")
                self.received_message.emit(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_message(self, message):
        self.socket.send(message.encode())

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.socket = socket.socket()
        self.connect_to_server()

    def connect_to_server(self):
        choice, okPressed = QInputDialog.getItem(self, "Get item", "Login (L) or Register (R)?", ["Login", "Register"], 0, False)
        if okPressed and choice:
            username, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your username:')
            password, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter your password:', QLineEdit.Password)
            if ok:
                self.socket.connect(('localhost', 50000))
                cmd = "REGISTER" if choice == "Register" else "LOGIN"
                credentials = f"{cmd} {username} {password}"
                self.socket.send(credentials.encode())
                self.client_thread = ClientThread(self.socket)
                self.client_thread.received_message.connect(self.update_chat)
                self.client_thread.start()
            else:
                self.close()
        else:
            self.close()

    def init_ui(self):
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        
        self.message_box = QLineEdit()
        self.message_box.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton('Envoyer')
        self.send_button.clicked.connect(self.send_message)
        
        layout = QVBoxLayout()
        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_box)
        layout.addWidget(self.send_button)

        self.setLayout(layout)
        self.setWindowTitle('Serveur Discord')
        self.resize(400, 300)

    def send_message(self):
        message = self.message_box.text()
        self.message_box.clear()
        if message:
            self.update_chat(f"Moi: {message}")  # Add the user's message to the chat history
            self.client_thread.send_message(message)

    def update_chat(self, message):
    # Vérifiez si le message est un message privé
        if "[PRIVATE]" in message:
            self.chat_history.setTextColor(QColor('orange'))
        else:
            self.chat_history.setTextColor(QColor('black'))

    # Ajoutez le message à l'historique de la discussion
        self.chat_history.append(message)

    # Réinitialiser la couleur pour le prochain message
        self.chat_history.setTextColor(QColor('black'))


    def closeEvent(self, event):
        self.socket.close()
        self.client_thread.terminate()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    chat_window = ChatWindow()
    chat_window.show()
    sys.exit(app.exec_())
