import sys
import socket
import json
import threading
from tkinter import Tk, Text, Button, Entry, Listbox, END, messagebox, simpledialog

class ClientApp:
    def __init__(self, root):
        self.root = root
        root.title("Chat Client")
        root.geometry("400x300")

        self.chat_history = Text(root, state='disabled', height=12)
        self.chat_history.pack()

        self.message_box = Entry(root)
        self.message_box.pack()
        self.message_box.bind("<Return>", self.send_message)

        self.send_button = Button(root, text='Envoyer', command=self.send_message)
        self.send_button.pack()

        self.user_list_widget = Listbox(root)
        self.user_list_widget.pack()

        self.socket = socket.socket()
        self.is_connected = False
        self.connect_to_server()

    def connect_to_server(self):
        choice = simpledialog.askstring("Get item", "Login (L) or Register (R)?")
        if choice and choice.lower() in ['l', 'r']:
            username = simpledialog.askstring('Input Dialog', 'Enter your username:')
            password = simpledialog.askstring('Input Dialog', 'Enter your password:', show='*')
            if username and password:
                try:
                    self.socket.connect(('localhost', 50000))
                    cmd = "REGISTER" if choice.lower() == 'r' else "LOGIN"
                    credentials = f"{cmd} {username} {password}"
                    self.socket.send(credentials.encode())

                    response = self.socket.recv(1024).decode()
                    if "successful" in response:
                        self.is_connected = True
                        threading.Thread(target=self.receive_messages, daemon=True).start()
                    else:
                        messagebox.showwarning("Warning", response)
                except socket.error as e:
                    messagebox.showerror("Connection Error", f"Unable to connect to the server: {e}")
            else:
                self.root.destroy()
        else:
            self.root.destroy()

    def receive_messages(self):
        while self.is_connected:
            try:
                message = self.socket.recv(1024).decode()
                if message:
                    try:
                        data = json.loads(message)
                        if data["type"] == "user_list":
                            self.root.after(0, self.update_user_list, data["users"])
                        else:
                            self.root.after(0, self.update_chat, message)
                    except json.JSONDecodeError:
                        self.root.after(0, self.update_chat, message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_message(self, event=None):
        message = self.message_box.get()
        self.message_box.delete(0, END)
        if message and self.is_connected:
            try:
                self.socket.send(message.encode())
                self.update_chat(f"Moi: {message}")
            except socket.error as e:
                messagebox.showerror("Sending Error", f"Unable to send the message: {e}")

    def update_chat(self, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(END, message + '\n')
        self.chat_history.config(state='disabled')
        self.chat_history.see(END)

    def update_user_list(self, user_list):
        self.user_list_widget.delete(0, END)
        for user in user_list:
            self.user_list_widget.insert(END, user)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.is_connected:
                self.socket.close()
            self.root.destroy()

if __name__ == '__main__':
    root = Tk()
    app = ClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
