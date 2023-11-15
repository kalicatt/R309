import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

class ClientThread(threading.Thread):
    def __init__(self, socket, update_chat_callback):
        super().__init__()
        self.socket = socket
        self.update_chat_callback = update_chat_callback
        self.daemon = True

    def run(self):
        while True:
            try:
                message = self.socket.recv(1024).decode()
                self.update_chat_callback(message)
            except:
                break

    def send_message(self, message):
        self.socket.send(message.encode())

class ChatWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Chat Client')
        self.geometry('400x300')

        self.chat_log = scrolledtext.ScrolledText(self, state='disabled')
        self.chat_log.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.message_var = tk.StringVar()
        self.message_entry = tk.Entry(self, textvariable=self.message_var)
        self.message_entry.pack(padx=10, fill=tk.X)
        self.message_entry.bind('<Return>', self.send_message)

        self.user_choice_dialog()

    def user_choice_dialog(self):
        choice = simpledialog.askstring("Choice", "Login (L) or Register (R)?", parent=self)
        if choice and choice.lower() == 'l':
            self.connect_to_server(False)  # False for login
        elif choice and choice.lower() == 'r':
            self.connect_to_server(True)   # True for register
        else:
            self.destroy()

    def connect_to_server(self, is_registering):
        username = simpledialog.askstring("Username", "Enter your username", parent=self)
        password = simpledialog.askstring("Password", "Enter your password", parent=self, show='*')

        if username and password:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('localhost', 50000))

            if is_registering:
                self.socket.send("REGISTER".encode())  # Send a special register command to the server

            self.socket.send(username.encode())
            self.socket.send(password.encode())

            self.client_thread = ClientThread(self.socket, self.update_chat)
            self.client_thread.start()
        else:
            self.destroy()

    def send_message(self, event=None):
        message = self.message_var.get()
        self.message_var.set('')
        if message:
            self.client_thread.send_message(message)

    def update_chat(self, message):
        self.chat_log.config(state='normal')
        self.chat_log.insert('end', message + '\n')
        self.chat_log.config(state='disabled')
        self.chat_log.yview('end')

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.socket.close()
            self.client_thread.join()
            self.destroy()

if __name__ == '__main__':
    app = ChatWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
