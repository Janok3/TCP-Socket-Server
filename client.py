import socket
import os
from tkinter import Tk, Label, Entry, Button, Listbox, filedialog, END, Frame
import threading
import time

# Client class
class Client:
    def __init__(self):
        self.command_socket = None
        self.heartbeat_socket = None
        self.notification_socket = None
        self.is_connected = False  # Initialize the connection state
        self.gui_setup()
    
    # GUI Setup
    def gui_setup(self):
        self.root = Tk()
        self.root.title("Client GUI")

        # Server Connection Fields
        Label(self.root, text="Server IP:").grid(row=0, column=0)
        self.server_ip_entry = Entry(self.root)
        self.server_ip_entry.grid(row=0, column=1)

        Label(self.root, text="Server Port:").grid(row=1, column=0)
        self.server_port_entry = Entry(self.root)
        self.server_port_entry.grid(row=1, column=1)

        Label(self.root, text="Your Name:").grid(row=2, column=0)
        self.client_name_entry = Entry(self.root)
        self.client_name_entry.grid(row=2, column=1)

        # Create a frame to hold the buttons
        button_frame = Frame(self.root)
        button_frame.grid(row=3, column=0, columnspan=2)  # Place the frame in the grid

        # Connect Button
        self.connect_button = Button(button_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=0, column=0, padx=(0, 2))  # No padding on the right

        # Disconnect Button
        self.disconnect_button = Button(button_frame, text="Disconnect", command=self.disconnect_from_server, state="disabled")
        self.disconnect_button.grid(row=0, column=1, padx=(2, 0))  # No padding on the left

        # Configure the button frame to center the buttons
        button_frame.grid_columnconfigure(0, weight=1)  # Allow the first column to expand
        button_frame.grid_columnconfigure(1, weight=1)  # Allow the second column to expand

        # Upload Button
        self.upload_button = Button(self.root, text="Upload File", command=self.upload_file, state="disabled")
        self.upload_button.grid(row=4, column=0, columnspan=2)

        # List Button
        self.list_button = Button(self.root, text="List Files", command=self.list_files, state="disabled")
        self.list_button.grid(row=5, column=0, columnspan=2)

        # Download Button
        self.download_button = Button(self.root, text="Download File", command=self.download_file, state="disabled")
        self.download_button.grid(row=6, column=0, columnspan=2)

        # Delete button
        self.delete_button = Button(self.root, text="Delete File", command=self.delete_file, state="disabled")
        self.delete_button.grid(row=7, column=0, columnspan=2)

        # Client Log
        Label(self.root, text="Client Log:").grid(row=8, column=0, columnspan=2)
        self.log_listbox = Listbox(self.root, width=50, height=20)
        self.log_listbox.grid(row=9, column=0, columnspan=2)


    def connect_to_server(self):
        if self.is_connected:
            self.log("Disconnecting from the current server...")
            self.close_connections()  # Close existing connections

        try:
            # Get the necessary information of the server
            server_ip = self.server_ip_entry.get()
            server_port = int(self.server_port_entry.get())
            client_name = self.client_name_entry.get()

            # Create command socket (for sending commands to the server)
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.connect((server_ip, server_port))
            self.command_socket.send(client_name.encode())

            # Create heartbeat socket (for making sure the server is running)
            self.heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.heartbeat_socket.connect((server_ip, server_port))

            # Create notification socket (for receiving notifications from the server)
            self.notification_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.notification_socket.connect((server_ip, server_port))

            # Start heartbeat listener in a separate thread
            threading.Thread(target=self.listen_for_heartbeat, daemon=True).start()

            # Start notification listener in a separate thread
            threading.Thread(target=self.listen_for_notifications, daemon=True).start()

            response = self.command_socket.recv(1024).decode()
            if "ERROR" in response: # If there is an error close the sockets and write the error in log and close sockets
                self.log(response)
                self.close_connections()  # Close sockets on error
            else:
                self.log(response)
                self.is_connected = True  # Set connected state to True
                self.upload_button.config(state="normal")       # Enable the upload button
                self.list_button.config(state="normal")         # Enable the list button
                self.download_button.config(state="normal")     # Enable the download button
                self.delete_button.config(state="normal")       # Enable the delete button
                self.disconnect_button.config(state="normal")   # Enable the disconnect button
                self.connect_button.config(state="disabled")    # Disable the connect button
                self.log("Connected successfully.")

        except Exception as e:
            self.log(f"Connection failed: {str(e)}")

    def listen_for_heartbeat(self):
        while True: # Keep listening for the heartbeat message to make sure the server is running
            try: 
                heartbeat_message = self.heartbeat_socket.recv(1024).decode()
                """ if heartbeat_message == "HEARTBEAT":
                    self.log("Received heartbeat from server.")
                else:
                    self.log("Unexpected message on heartbeat connection.") """
            except Exception as e:
                # self.log("Connection to server has been lost")
                self.disconnect_from_server()
                break


    def download_file(self):
        try:
            # Request the list of files from the server
            self.command_socket.send("LIST".encode())   
            file_list = self.command_socket.recv(4096).decode().strip()
            
            # Check if the file list is empty
            if not file_list:
                self.log("No files available for download.")
                return

            # Open a new window to display the list of files
            self.open_file_selection_window(file_list)
        except Exception as e:
            self.log(f"Failed to request file list: {str(e)}")
    
    def open_file_selection_window(self, file_list):
        # Create a new window
        window = Tk()
        window.title("Select a File to Download")

        # Display the list of files
        Label(window, text="Available Files:").pack()
        file_listbox = Listbox(window, width=50, height=20)
        file_listbox.pack()

        # Populate the listbox
        files = file_list.split("\n")
        for file_entry in files:
            file_listbox.insert(END, file_entry)

        def confirm_download():
            selected = file_listbox.get(file_listbox.curselection()) # Get the selected file
            if selected:
                filename, owner = selected.split(": ", 1)
                window.destroy()  # Close the selection window
                self.download_selected_file(owner.strip(), filename.strip()) # Download the selected file

        Button(window, text="Download", command=confirm_download).pack()

        # Run the window's event loop
        window.mainloop()

    def download_selected_file(self, owner, filename):
        try:
            # Send the download request
            self.log(f"Requesting download for {owner}: {filename}")
            self.command_socket.send(f"DOWNLOAD {owner} {filename}".encode())
            
            response = self.command_socket.recv(1024).decode() # Get the response of the server
            
            if response.startswith("ERROR"): # Check if there are any errors
                self.log(response)
                return

            # Get the file size
            _, file_size = response.split(" ", 1)
            file_size = int(file_size)

            # Save the file with the original filename
            save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=filename)
            if not save_path:
                return

            with open(save_path, "wb") as f: # Open the file in binary write mode
                received = 0  
                while received < file_size: # Loop until all data is received
                    data = self.command_socket.recv(1024) # Receive data in chunks of 1024 bytes
                    f.write(data) 
                    received += len(data) # Update the amount of data received

            self.log(f"File {filename} downloaded successfully.")
        except Exception as e:
            self.log(f"Download failed: {str(e)}")


    def upload_file(self):
        try:
            filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")]) # Prompt the user to select a file to upload
            if not filepath:
                return # Exit if no file is selected

            filename = os.path.basename(filepath) # Extract the filename 
            filename = filename.replace(" ", "_") # Replace spaces with underscores
            file_size = os.path.getsize(filepath) # Extract the file size

            self.command_socket.send(f"UPLOAD {filename} {file_size}".encode()) # Send the filename and file size to the server

            with open(filepath, "rb") as f:
                while chunk := f.read(1024):  # Read the file in chunks of 1024 bytes
                    self.command_socket.send(chunk) # Send each chunk to the server

            response = self.command_socket.recv(1024).decode() # Receive the server's response to the upload
            self.log(response)
        except Exception as e:
            self.log(f"Upload failed: {str(e)}") 


    def list_files(self):
        try:
            self.log("Requesting file list...")
            # Send the LIST command to the server to request the file list
            self.command_socket.send("LIST".encode())
            # Receive the file list from the server
            file_list = self.command_socket.recv(4096).decode()
            
            # Log the received file list with each file on a different line
            self.log("Available files:")
            for file in file_list.split("\n"):
                self.log(file)
        
        except Exception as e:
            self.log(f"Failed to list files: {str(e)}")

    def log(self, message):
        self.log_listbox.insert(END, message)
        self.log_listbox.see(END)
        self.root.update_idletasks() # Force the GUI to update

    def delete_file(self):
        try:
            # Request and recieve the list of files 
            self.command_socket.send("LIST".encode())
            file_list = self.command_socket.recv(4096).decode().strip()
            
            # Check if the list is empty
            if not file_list:
                self.log("No files available for deletion.")
                return

            # Open a new window to display the list of files
            self.open_file_deletion_window(file_list)
        except Exception as e:
            self.log(f"Failed to request file list for deletion: {str(e)}")

    def open_file_deletion_window(self, file_list):
        # Create a new window
        window = Tk()
        window.title("Select a File to Delete")

        # Display the list of files
        Label(window, text="Uploaded Files:").pack()
        file_listbox = Listbox(window, width=50, height=20)
        file_listbox.pack()

        # Populate the listbox
        files = file_list.split("\n")
        for file_entry in files:
            file_listbox.insert(END, file_entry)

        def confirm_delete():
            selected = file_listbox.get(file_listbox.curselection()) # Get the selection
            if selected:
                filename, owner = selected.split(": ", 1)
                window.destroy()  # Close the selection window
                self.delete_selected_file(owner.strip(), filename.strip())

        Button(window, text="Delete", command=confirm_delete).pack()

        # Run the window's event loop
        window.mainloop()

    def delete_selected_file(self, owner, filename):
        try:
            self.log(f"Requesting delete for {owner}: {filename}") # Write the request in the log

            self.command_socket.send(f"DELETE {owner} {filename}".encode()) # Send the delete request to server
            response = self.command_socket.recv(1024).decode() # Recieve the response from the server

            if response.startswith("ERROR"): # Check if there is an error in the response
                self.log(response)
                return
            
            self.log(response)
            
        except Exception as e:
            self.log(f"Deletion failed: {str(e)}")

    def listen_for_notifications(self):
        while True: # Listen for any notifications from the server
            try:
                notification = self.notification_socket.recv(1024).decode()
                if notification:
                    self.log(notification)  # Display the notification in the client log
            except Exception as e:
                """ self.log(f"Error while listening for notifications: {str(e)}") """
                break

    def run(self):
        # Start the GUI main loop
        self.root.mainloop()

    def close_connections(self):
        # Close all sockets and reset connection state
        if self.command_socket:
            self.command_socket.close()
            self.command_socket = None
        if self.heartbeat_socket:
            self.heartbeat_socket.close()
            self.heartbeat_socket = None
        if self.notification_socket:
            self.notification_socket.close()
            self.notification_socket = None
        self.is_connected = False  # Reset connection state

    def disconnect_from_server(self):
        if self.is_connected:
            self.log("Disconnecting from the server...")
            self.close_connections()  # Close existing connections
            self.disconnect_button.config(state="disabled")     # Disable the disconnect button
            self.connect_button.config(state="normal")          # Enable the connect button
            self.upload_button.config(state="disabled")         # Disable the upload button
            self.list_button.config(state="disabled")           # Disable the list button
            self.download_button.config(state="disabled")       # Disable the download button
            self.delete_button.config(state="disabled")         # Disable the delete button
            self.log("Disconnected successfully.")
        else:
            self.log("Not connected to any server.")


if __name__ == "__main__":
    client = Client()
    client.run()
