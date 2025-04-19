import socket
import magic
import threading
from PIL import Image
from io import BytesIO
import os
from pydub import AudioSegment
from moviepy import VideoFileClip
from OpenSSL import SSL



def recv_line(sock):
    buffer = b""
    while not buffer.endswith(b"\n"):
        buffer += sock.recv(1)
    return buffer[:-1].decode()

def handle_client(client):
    try:
        file_name = recv_line(client)
        file_size = recv_line(client)

        # conversion_type = client.recv(1024).decode()

        file_data = b""
        while not file_data.endswith(b"<END>"):
            data = client.recv(1024)
            file_data += data
        file_data = file_data[:-5]

        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(file_data)
        print("Detected file MIME type:", file_mime_type)

        # image_file_type = (".png", ".jpeg", ".jpg", ".bmp", ".tiff", ".gif", ".webp")

        if file_mime_type.startswith("image/"):
            client.send(str((".png", ".jpeg", ".jpg", ".bmp", ".tiff", ".gif", ".webp")).encode())
            conversion_type = client.recv(1024).decode().strip()
            image_data = BytesIO(file_data)  # using ByteIO so that i dont have to save the file in server instead use ram buffer
            img = Image.open(image_data)
            if conversion_type in ["jpeg", "jpg"]:
                conversion_type = "jpeg"
                img = img.convert("RGB")
            image_output = BytesIO()
            img.save(image_output, format=conversion_type.upper())
            converted_file = image_output.getvalue()
            client.sendall(converted_file)
            client.send(b"<END1>")
            client.recv(1024).decode()
            image_output.close()
            image_data.close()

        # handle with pydub
        elif file_mime_type.startswith("audio/"):
            # audio_file_type = client.recv(1024).decode().strip()
            audio_file_type = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".aiff", ".wma")
            # if file_name.endswith(audio_file_type):
            client.send(str(audio_file_type).encode())
            conversion_type = client.recv(1024).decode()
            audio_data = BytesIO(file_data)
            audio_output = BytesIO()
            AudioSegment.from_file(audio_data).export(audio_output, format=conversion_type)
            converted_file = audio_output.getvalue()
            client.sendall(converted_file)
            client.send(b"<END1>")
            client.recv(1024).decode()
            audio_output.close()
            audio_data.close()

            
        elif file_mime_type.startswith("video/"):
            video_file_type = (".mp4", ".webm", ".avi", ".mov", ".mkv")
        # if file_name.endswith(video_file_type):
            client.send(str(video_file_type).encode())
            conversion_type = client.recv(1024).decode()
            file_ext = file_name.split(".")[-1]
            with open("serverfile."+file_ext, "wb") as f:
                f.write(file_data)
            clip = VideoFileClip("serverfile."+file_ext)
            clip.write_videofile("serveroutput."+conversion_type)
            with open("serveroutput."+conversion_type, "rb") as f:
                converted_file = f.read()
            os.remove("serveroutput."+conversion_type)
            os.remove("serverfile."+file_ext)
            client.sendall(converted_file)
            client.send(b"<END1>")
            client.recv(1024).decode()

        elif file_mime_type in ["text/markdown", "text/plain", "text/html", "application/pdf"]:
            client.send(str((".md", ".html", ".txt", ".pdf")).encode())
            # handle with pypandoc
        else:
            client.send(str(("Unsupported file type",)).encode())

        new_file_name = file_name.split('.')
        new_file_name[-1] = conversion_type
        new_file_name = 'converted' + '.'.join(new_file_name)
        client.send(new_file_name.encode())

    except Exception as e:
        print("Error while handling client:", e)
    finally:
        client.close()

ctx = SSL.Context(SSL.TLSv1_2_METHOD)
ctx.use_privatekey_file('key')          #'key' file required in server location
ctx.use_certificate_file('cert')        #'cert' file required in server location

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 8000))
server.listen()
print("Server listening on port 8000...")

while True:
    client_sock, addr = server.accept()
    client = SSL.Connection(ctx, client_sock)
    client.set_accept_state()
    print(f"Connected to {addr}")
    threading.Thread(target=handle_client, args=(client,)).start()