import socket
import os
from OpenSSL import SSL

ctx = SSL.Context(SSL.TLSv1_2_METHOD)
ctx.set_options(SSL.OP_NO_SSLv2 | SSL.OP_NO_SSLv3)

client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client = SSL.Connection(ctx, client_sock)
client.connect(("localhost", 8000))

file = "clientVideo.mp4"

with open(file, "rb") as f:
    data = f.read()

file_size = os.path.getsize(file)

client.send(file.encode())
client.send(str(file_size).encode())

client.sendall(data)
client.send(b"<END>")

file_type = client.recv(1024).decode()
file_type = tuple(x.strip("'") for x in file_type.strip("()").split(", "))  # to convert string back to tuple
print("File sent can be converted to:")
for i in file_type:
    print(i[1:])

conversion_type = input()
client.send(conversion_type.encode())

file_data = b""
while not file_data.endswith(b"<END1>"):
    recv_data = client.recv(1024)
    file_data += recv_data
    # print(file_data)
client.send("received".encode())
new_file_name = client.recv(1024).decode()

with open(new_file_name, "wb") as f:
    f.write(file_data[:-6])
client.close()