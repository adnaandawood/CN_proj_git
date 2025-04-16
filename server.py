import socket
from PIL import Image
from io import BytesIO
import pypandoc
import os
import subprocess
from pydub import AudioSegment
from moviepy import VideoFileClip

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
    image_output.close()
    image_data.close()

doc_file_type = (".md", ".docx", ".html", ".ipynb", ".tex", ".epub", ".csv")
if file_name.endswith(doc_file_type):
    client.send(str(doc_file_type).encode())
    conversion_type = client.recv(1024).decode()
    file_ext = file_name.split('.')[-1]
    with open("serverfile."+file_ext, "wb") as f:
        f.write(file_data)
    # pypandoc.convert_file("serverfile."+file_ext, conversion_type, format=file_ext, outputfile="serveroutput."+conversion_type, extra_args=["--pdf-engine=pdflatex"])
    # subprocess.run(["pandoc", "serverfile."+file_ext, "-f", file_ext, "-t", conversion_type, "-o", "serveroutput."+conversion_type, "--pdf-engine=pdflatex"], check=True)
    os.system(f"pandoc serverfile.{file_ext} -f {file_ext} -t {conversion_type} -o serveroutput.{conversion_type}")
    with open("serveroutput."+conversion_type, "rb") as f:
        converted_file = f.read()
    os.remove("serveroutput."+conversion_type)
    os.remove("serverfile."+file_ext)
    
audio_file_type = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".aiff", ".wma")
if file_name.endswith(audio_file_type):
    client.send(str(audio_file_type).encode())
    conversion_type = client.recv(1024).decode()
    audio_data = BytesIO(file_data)
    audio_output = BytesIO()
    AudioSegment.from_file(audio_data).export(audio_output, format=conversion_type)
    converted_file = audio_output.getvalue()
    audio_output.close()
    audio_data.close()

video_file_type = (".mp4", ".webm", ".avi", ".mov", ".mkv")
if file_name.endswith(video_file_type):
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
new_file_name = file_name.split('.')
new_file_name[-1] = conversion_type
new_file_name = 'converted' + '.'.join(new_file_name)
client.send(new_file_name.encode())

server.close()
client.close()