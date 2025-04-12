import socket
from PIL import Image
from io import BytesIO

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 8000))
server.listen()
client, addr = server.accept()

file_name = client.recv(1024).decode()
file_size = client.recv(1024).decode()
# conversion_type = client.recv(1024).decode()

file_data = b""
while not file_data.endswith(b"<END>"):
    data = client.recv(1024)
    file_data += data
file_data = file_data[:-5]

image_file_type = (".png", ".jpeg", ".jpg", ".bmp", ".tiff", ".gif", ".webp")
if file_name.endswith(image_file_type):
    client.send(str(image_file_type).encode())
    conversion_type = client.recv(1024).decode()
    image_data = BytesIO(file_data)  # using ByteIO so that i dont have to save the file in server instead use ram buffer
    img = Image.open(image_data)
    if conversion_type in ["jpeg", "jpg"]:
        conversion_type = "jpeg"
        img = img.convert("RGB")
    image_output = BytesIO()
    img.save(image_output, conversion_type.upper())
    converted_file = image_output.getvalue()
    client.sendall(converted_file)
    client.send(b"<END1>")
    client.recv(1024).decode()
    image_output.close()
    image_data.close()
    
    new_file_name = file_name.split('.')
    new_file_name[-1] = conversion_type
    new_file_name = 'converted' + '.'.join(new_file_name)
    client.send(new_file_name.encode())

server.close()
client.close()