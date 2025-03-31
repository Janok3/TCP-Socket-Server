import socket
import threading
import os
from tkinter import Tk, Label, Entry, Button, Listbox, filedialog, END
import time

# Server class to handle client connections and file operations
class Server:
    def __init__(self):
        self.command_sockets = {}       # Dictionary to store connected command connections
        self.heartbeat_sockets = {}     # Dictionary for heartbeat connections
        self.notification_sockets = {}  # Dictionary for notification connections
        self.files = {}                 # Dictionary to keep track of uploaded files
        self.server_socket = None       # Socket for the server
        self.storage_path = ""          # Path for storing uploaded files
        self.gui_setup()                # Set up the GUI
        self.running = False            # Flag to control server running state

    def gui_setup(self):
        # Initialize the GUI components
        self.root = Tk()
        self.root.title("Server GUI")
        
        # Port input
        Label(self.root, text="Port:").grid(row=0, column=0)
        self.port_entry = Entry(self.root)
        self.port_entry.grid(row=0, column=1)

        # Folder selection for storage
        Button(self.root, text="Set Storage Folder", command=self.select_folder).grid(row=1, column=0, columnspan=2)

        # Start button
        self.start_button = Button(self.root, text="Start Server", command=self.start_server, state="disabled")
        self.start_button.grid(row=2, column=0, columnspan=2)

        # Log display
        Label(self.root, text="Server Log:").grid(row=3, column=0, columnspan=2)
        self.log_listbox = Listbox(self.root, width=50, height=20)
        self.log_listbox.grid(row=4, column=0, columnspan=2)

    def select_folder(self):
        self.files = {} # Reset the files dictionary to account for the case that the user selects one path after another
                        # This makes sure that only the latest selected directory will be considered
        self.storage_path = filedialog.askdirectory() # Open folder dialog

        self.log(f"Storage folder set to: {self.storage_path}")
        for filename in os.listdir(self.storage_path):
            self.files[filename] = filename.split("_")[0] # Store files with their owners
        
        if self.storage_path:
            self.start_button.config(state="normal") # Enable the start button

    def start_server(self):
        # Start the server and listen for incoming connections
        port = int(self.port_entry.get())
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", port)) # Bind to all interfaces
        self.server_socket.listen(5) # Listen for incoming connections
        self.log(f"Server started on port {port}")
        self.running = True
        threading.Thread(target=self.accept_connections, daemon=True).start()   # Accept connections in a separate thread
        threading.Thread(target=self.send_heartbeat, daemon=True).start()       # Send heartbeats in a separate thread

    def accept_connections(self):
        # Accept incoming client connections
        while self.running:
            client_socket, _ = self.server_socket.accept()          # Accept command socket
            heartbeat_socket, _ = self.server_socket.accept()       # Accept heartbeat socket
            notification_socket, _ = self.server_socket.accept()    # Accept notification socket

            # Handle the client in a new thread
            threading.Thread(target=self.handle_client, args=(client_socket, heartbeat_socket, notification_socket), daemon=True).start()

    def handle_client(self, command_socket, heartbeat_socket, notification_socket):
        # Handle communication with a connected client
        client_name = command_socket.recv(1024).decode()  # Receive client name
        
        # Check if the client name is already in use
        if client_name in self.command_sockets:
            command_socket.send("ERROR: Name already in use.".encode())
            self.log(f"{client_name} is already in use. The new client was not accepted.")
            command_socket.close()          # Close command socket
            heartbeat_socket.close()        # Close heartbeat socket 
            notification_socket.close()     # Close notification socket
            return

        # If the name is not in use, proceed to add the client
        self.command_sockets[client_name] = command_socket              # Store command socket
        self.heartbeat_sockets[client_name] = heartbeat_socket          # Store heartbeat socket
        self.notification_sockets[client_name] = notification_socket    # Store notification socket
        
        self.log(f"{client_name} connected.")
        command_socket.send("Welcome to the server!".encode())

        while True:
            try:
                command = command_socket.recv(1024).decode()  # Receive command from client
                if not command:  # Check if command is empty (client disconnected)
                    break
                if command == "LIST":
                    self.send_file_list(command_socket)
                elif command.startswith("UPLOAD"):
                    self.handle_upload(command_socket, client_name, command)
                elif command.startswith("DOWNLOAD"):
                    self.handle_download(command_socket, command, client_name)
                elif command.startswith("DELETE"):
                    self.handle_delete(command_socket, command, client_name)
                elif command == "EXIT":
                    break
            except (ConnectionResetError, BrokenPipeError):
                break

        # Clean up on disconnect
        self.disconnect_client(client_name, command_socket, heartbeat_socket, notification_socket)

    def send_heartbeat(self):
        # Send heartbeat messages to connected heartbeat socket
        while self.running:
            for client_name, heartbeat_socket in list(self.heartbeat_sockets.items()):
                try:
                    heartbeat_socket.send("HEARTBEAT".encode()) # Send heartbeat
                except (BrokenPipeError, ConnectionResetError):
                    self.disconnect_client(client_name, self.command_sockets[client_name], heartbeat_socket, self.notification_sockets[client_name])
            time.sleep(2) # Send heartbeat every 2 seconds

    def handle_download(self, client_socket, command, client_name):
        try:
            # Extract owner and filename
            _, owner, filename  = command.split(" ", 2)
            file_key = filename  # Format should be 'owner_filename'

            # This check is not necessary since the client can't pick a file that doesn't exist 
            """ if file_key not in self.files:
                client_socket.send("ERROR: File not found.".encode())
                return """

            filepath = os.path.join(self.storage_path, file_key)    # Construct file path
            file_size = os.path.getsize(filepath)                   # Get file size

            client_socket.send(f"OK {file_size}".encode()) # Send file size to client

            with open(filepath, "rb") as f:
                while chunk := f.read(1024): # Read and send file in chunks
                    client_socket.send(chunk)

            self.log(f"File {filename} sent to {client_name}.")

            # Notify the owner of the file about the download only if the downloader is not the owner
            if owner != client_name:
                if owner in self.notification_sockets:
                    owner_socket = self.notification_sockets[owner]
                    owner_socket.send(f"NOTICE: Your file '{filename}' has been downloaded by {client_name}.".encode())
                    self.log(f"Notified {owner} about the download of their file '{filename}' by {client_name}.")
                else:
                    self.log(f"Owner {owner} is not connected. Cannot send notification.")

        except Exception as e:
            self.log(f"Error during download: {str(e)}")
            client_socket.send("ERROR: Download failed.".encode())

    def disconnect_client(self, client_name, command_socket, heartbeat_socket, notification_socket):
        if client_name in self.command_sockets:
            del self.command_sockets[client_name]       # Remove command socket from the dictionary
            del self.heartbeat_sockets[client_name]     # Remove heartbeat socket from the dictionary
            del self.notification_sockets[client_name]  # Remove notification socket from the dictionary

            self.log(f"{client_name} has been disconnected.")

            command_socket.close()                      # Close the command socket
            heartbeat_socket.close()                    # Close the heartbeat socket
            notification_socket.close()                 # Close the notification socket

    def send_file_list(self, command_socket):
        # Construct the file list
        file_list = "\n".join([f"{owner}: {filename}" for owner, filename in self.files.items()])
        
        if not file_list: # Check if the file list is empty
            command_socket.send("No files available.".encode())
            return
        
        command_socket.send(file_list.encode()) # Send the file list to the client      

    def handle_upload(self, command_socket, client_name, command):
        try:
            _, filename, file_size = command.split(" ", 2) # Extract the file name and file size from the command
            file_size = int(file_size) # Convert file size to integer
            
            # Construct the file path
            file_key = f"{client_name}_{filename}"  # Construct the key for the file
            filepath = os.path.join(self.storage_path, file_key)  # Full path for the file

            # Check if the file already exists
            file_exists = os.path.exists(filepath)

            # Open the file in write binary mode
            with open(filepath, "wb") as f:
                received = 0
                # Receive the file data in chunks and write to the file
                while received < file_size:
                    data = command_socket.recv(1024)
                    f.write(data)
                    received += len(data)

            # Add the file to the server's files dictionary
            self.files[file_key] = client_name  # Store the file with the client name

            if file_exists:  # Check if the file already existed
                self.log(f"Upload successful, {client_name} overwrote {filename}.")
                command_socket.send(f"Upload successful, {filename} was overwritten".encode())
            else:
                self.log(f"{client_name} uploaded {filename}.")
                command_socket.send("Upload successful.".encode())

        except Exception as e:
            self.log(f"Error during upload: {str(e)}")
            print(str(e))
            command_socket.send("UPLOAD_FAILED".encode())

    def handle_delete(self, command_socket, command, client_name):
        try:
            # Extract owner and filename
            _, owner, filename  = command.split(" ", 2)
            file_key = filename 

            # This check is not necessary since the user cannot pick a file that doesnt exist
            """ if file_key not in self.files:
                command_socket.send("ERROR: File not found.".encode())
                return """

            if owner != client_name: # Check if the file was uploaded by the client
                command_socket.send("ERROR: You do not have permission to delete this file.".encode())
                return

            # Delete the file from the server's storage
            file_path = os.path.join(self.storage_path, file_key)
            os.remove(file_path)  # Remove the file from the filesystem
            del self.files[file_key]  # Remove the file from the files dictionary
            
            command_socket.send("File deleted successfully.".encode())
            self.log(f"{client_name} deleted {filename}.")
        except Exception as e:  
            self.log(f"Error during deletion: {str(e)}")
            command_socket.send("ERROR: Deletion failed.".encode())

    def log(self, message):
        self.log_listbox.insert(END, message)
        self.log_listbox.see(END)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    server = Server()
    server.run()
