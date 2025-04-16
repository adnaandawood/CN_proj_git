# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import os
import socket
import io
import uuid
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def convert_file(file_path, original_filename, conversion_type, session_id):

    print("nodappa",conversion_type)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        
        client.connect(("localhost", 8000))
        print("try")
        with open(file_path, "rb") as f:
            data = f.read()

        file_size = os.path.getsize(file_path)

        client.send((original_filename + "\n").encode())
        client.send((str(file_size) + "\n").encode())
        client.sendall(data)
        client.send(b"<END>")

        # Receive supported conversion types
        file_types_str = client.recv(1024).decode()
        file_types = tuple(x.strip("'\"") for x in file_types_str.strip("()").split(", "))

        
        # Check if conversion type is supported
        if conversion_type not in [t.lstrip(".") for t in file_types]:
            session['error'] = f"Conversion type {conversion_type} not supported for this file."
            client.close()
            return None

        # Send chosen conversion type
        client.send(conversion_type.encode())
        # Receive converted file
        file_data = b""
        while not file_data.endswith(b"<END1>"):
            recv_data = client.recv(1024)
            if not recv_data:
                break
            file_data += recv_data
            
        client.send("received".encode())
        new_file_name = client.recv(1024).decode()
        
        # Save the converted file
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{new_file_name}")
        with open(output_path, "wb") as f:
            f.write(file_data[:-6])  # Remove <END1> marker
        
        return {'path': output_path, 'name': new_file_name}
    except Exception as e:
        print(f"[Client Error] {e}")
        session['error'] = f"Conversion error: {str(e)}"
        return None

    finally:
        client.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
        
    if file:
        # Generate a session ID for this conversion
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)
        
        # Get the file mime type
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(("localhost", 8000))
            
            with open(file_path, "rb") as f:
                data = f.read()

            file_size = os.path.getsize(file_path)

            client.send((filename + "\n").encode())
            client.send((str(file_size) + "\n").encode())
            client.sendall(data)
            client.send(b"<END>")

            # Receive supported conversion types
            file_types_str = client.recv(1024).decode()
            if file_types_str.startswith("Unsupported"):
                flash('This file type is not supported for conversion')
                return redirect(url_for('index'))
                
            file_types = tuple(x.strip("'\"") for x in file_types_str.strip("()").split(", "))
            conversion_options = [t.lstrip(".") for t in file_types]
            
            # Close the connection - we'll create a new one for the actual conversion
            client.close()
            
            # Store info in session
            session['file_path'] = file_path
            session['original_filename'] = filename
            session['conversion_options'] = conversion_options
            
            return redirect(url_for('select_conversion'))
            
        except Exception as e:
            flash(f"Error: {str(e)}")
            return redirect(url_for('index'))
        finally:
            client.close()

@app.route('/select_conversion')
def select_conversion():
    if 'file_path' not in session:
        return redirect(url_for('index'))
    print("Conversion options:", session['conversion_options'])
    return render_template(
        'select_conversion.html',
        filename=session['original_filename'],
        options=session['conversion_options']
    )

@app.route('/convert', methods=['POST'])
def convert():
    print("entered convert route")
    if 'file_path' not in session:
        return redirect(url_for('index'))
        
    if request.method == "POST":
        data = request.get_json()
        conversion_type= data.get("selectedOption")
        print("typeee",conversion_type)
        # conversion_type=data.get("selectedOption")

    if not conversion_type:
        flash('No conversion type selected')
        return redirect(url_for('select_conversion'))
    
    # Run conversion in a thread to avoid blocking
    result = convert_file(
        session['file_path'], 
        session['original_filename'], 
        conversion_type,
        session['session_id']
    )
    
    print("ress", result)
    if result is None:
        flash(session.get('error', 'Unknown conversion error'))
        return redirect(url_for('index'))
    
    session['converted_file'] = result
    return {"success": True, "redirect": url_for('download')}

@app.route('/download')
def download():
    if 'converted_file' not in session:
        return redirect(url_for('index'))
        
    file_info = session['converted_file']
    return render_template('download.html', filename=file_info['name'])

@app.route('/get_file')
def get_file():
    if 'converted_file' not in session:
        return redirect(url_for('index'))
        
    file_info = session['converted_file']
    return send_file(
        file_info['path'],
        as_attachment=True,
        download_name=file_info['name']
    )

@app.route('/reset')
def reset():
    # Clean up session data
    if 'file_path' in session and os.path.exists(session['file_path']):
        try:
            os.remove(session['file_path'])
        except:
            pass
            
    if 'converted_file' in session and os.path.exists(session['converted_file']['path']):
        try:
            os.remove(session['converted_file']['path'])
        except:
            pass
    
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)