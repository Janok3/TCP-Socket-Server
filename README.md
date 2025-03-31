# TCP File Storage Server

This project implements a simple TCP-based file storage server and client. The server allows clients to upload, download, and list files over a TCP connection. The client provides an interface to interact with the server for file operations.

## Files
- **`server.py`**: The server-side script that listens for client connections and handles file storage operations.
- **`client.py`**: The client-side script that connects to the server and allows users to upload, download, or list files.

## Features
- Upload files to the server.
- Download files from the server.
- List available files stored on the server.
- Simple TCP-based communication between client and server.

## Prerequisites
- Python 3.x installed on your system.
- Both client and server must be running on machines that can communicate over a network (e.g., localhost or a LAN).

## Installation
1. Clone or download this repository to your local machine.
2. Ensure you have Python 3.x installed:
3. Place both server.py and client.py in your desired directory.

## Usage
### Runnning the Server
1. Open a terminal and navigate to the directory containing server.py.
2. Start the server by running:
```console
python3 server.py
```
3. Select a storage folder.
4. Type a port number and press start server.

### Running the Client
1. Open a separate terminal and navigate to the directory containing client.py.
1. Start the client by running:
```console
python3 client.py
```
3. Enter the IP address of the host machine and press connect.


## Contributors 

- Janok N. Dinçer
- Alp Demir Ekinci
