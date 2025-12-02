import os
import boto3
from flask import Flask, render_template_string, request, jsonify, flash, render_template, redirect, url_for, send_file
from werkzeug.utils import secure_filename # will remove Chinese chars from the filename
from datetime import datetime
import io
import uuid

# ====== Configuration ======
AWS_S3_BUCKET = 'rag-file-storage-bucket'  # <-- Change this!
ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx'}
UPLOAD_FOLDER = '/uploads'  # Temporary storage before S3 upload

s3 = boto3.client('s3')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your_secret_key'

# ====== Helper functions ======
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ====== Routes ======
# @app.route('/', methods=['GET'])
# def index():
#     return render_template_string(HTML)

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     file = request.files.get('file')
#     if not file or not allowed_file(file.filename):
#         return jsonify(success=False, error='Invalid file type (allowed: pdf, xls, xlsx)')
    
#     filename = secure_filename(file.filename)
#     file_ext = filename.rsplit('.', 1)[-1].lower()
#     local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#     file.save(local_path)
    
#     try:
#         # Upload to S3
#         s3.upload_file(local_path, AWS_S3_BUCKET, filename)
#         file_info = {
#             'filename': filename,
#             'type': file_ext,
#             'size': os.path.getsize(local_path),
#             'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         }
#         os.remove(local_path)
#         return jsonify(success=True, file=file_info)
#     except Exception as e:
#         return jsonify(success=False, error=str(e))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list-files')
def list_files():
    try:
        response = s3.list_objects_v2(Bucket=AWS_S3_BUCKET)
        files = []

        if 'Contents' in response:
            for item in response['Contents']:
                files.append({
                    'key': item['Key'],
                    'size': round(item['Size'] / 1024, 2),
                    'last_modified': item['LastModified'].isoformat(),  # Convert to string
                })
        
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    try:
        # Get additional form data
        custom_filename = request.form.get('filename', '').strip()
        authors = request.form.get('authors', '').strip()
        language = request.form.get('language', '')
        
        # source_filename = secure_filename(file.filename) # strips Chinese
        source_filename = os.path.basename(file.filename) # keeps Chinese, strips paths
        if not source_filename:
            flash('Invalid filename')
            return redirect(url_for('index'))

        file_id = str(uuid.uuid4())
        file_s3_key = f"{file_id}/{source_filename}"
        
        # Store metadata (you'd want to save this to database)
        metadata = {
            'id': file_id,
            'source_filename': source_filename,
            'filename': custom_filename,
            'author': authors,
            'language': language,
            'date_added': datetime.now(),
            'size': file.content_length, # problem
            "pages": 0,
            'status': 0, # 0: uploaded not processed, 1: processed
            's3_key': file_s3_key,
            
        }
        print(metadata)

        s3.upload_fileobj(file, AWS_S3_BUCKET, file_s3_key, ExtraArgs={
            'Metadata': {
                'id': file_id,
            },
            'ContentType': file.content_type
            })
        flash(f"File {file_s3_key} uploaded successfully")
    
    except Exception as e:
        flash(f"ERROR UPLOADING FILE: {str(e)}")
    
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_obj = io.BytesIO()
        s3.download_fileobj(AWS_S3_BUCKET, filename, file_obj)
        file_obj.seek(0)

        return send_file(
            file_obj,
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        flash(f"ERROR DOWNLOADING FILE: {str(e)}")
        return redirect(url_for('index'))


@app.route('/delete/<filename>')
def delete_file(filename):
    try:
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=filename)
        flash(f"File {filename} deleted successfully")
    except Exception as e:
        flash(f"ERROR DELETING FILE: {str(e)}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
