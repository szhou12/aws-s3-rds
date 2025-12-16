# AWS S3 File Manager

This project provides two different implementations of an S3 file manager:

1. **Flask Web App** (`app_flask.py`) - Traditional web app with HTML templates
2. **Streamlit App** (`app_streamlit.py`) - Modern, interactive dashboard
3. **FASTAPI** (`app_fastapi.py`)

## Setup
```bash
# initialize a project in the working directory
$ uv init

# create a virtual env with default name
$ uv venv --python 3.13

# activate the environment
$ source .venv/bin/activate
# automatically activate the virtual environment
Cmd + Shift + P -> Python: Select Interpreter -> type to find .venv

# install all dependencies
$ uv add <dependency>
$ uv sync


```

## Running the Applications

### FastAPI Version
```bash
uv run app_fastapi.py
```

### Flask Version
```bash
python app_flask.py
```
Then open http://localhost:5000 in your browser.

### Streamlit Version
```bash
streamlit run app_streamlit.py
```
The app will automatically open in your browser.

## Configuration

Update the `AWS_S3_BUCKET` variable in both `app_flask.py` and `app_streamlit.py` to point to your S3 bucket.

Make sure your AWS credentials are configured either through:
- AWS CLI (`aws configure`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- IAM roles (if running on EC2)

## Features

Both versions provide:
- File upload to S3 (PDF, XLS, XLSX)
- File listing from S3
- File download from S3
- File deletion from S3

The Streamlit version additionally offers:
- Modern, interactive UI
- Real-time file processing status
- Better visual feedback and error handling

# Workflow Diagram
```
   [1. Staff User]
           |
           v
   [2. Frontend UI]
           |
           v
   [3. RAG App Backend (FastAPI, EC2/ECS)]
        |                |
   (3a) Save metadata    |
         to RDS MySQL    |
        |                |
        |          (3b) Upload file
        |                |   (S3 SDK)
        |                v
        |        [4. S3 Bucket (uploads)]
        |                |
        |         (S3 Event Trigger)
        |                v
        |        [5. Lambda Function]
        |             (serverless processing)
        |                |
        |          --------------
        |          |            |
        v          v            v
 [6a. Update    [6b. Extract   [6c. Generate
  status in      text from      embeddings/
   RDS]          document]      index docs]
        |          |            |
        |          |            |
        +----------+------------+
                   |
                   v
         [7. Store results in S3, RDS, or Search Service]

```

# Metadata Schemas
```
CREATE TABLE Upload (
    id INT PRIMARY KEY AUTO_INCREMENT,
    filename VARCHAR(255),
    author VARCHAR(255),
    language VARCHAR(16),
    filepath VARCHAR(512),
    size INT, -- MB
    status VARCHAR(32), -- "uploaded", "processing", "parsed", "failed"
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    parsed_at DATETIME DEFAULT NULL
);

CREATE TABLE FilePage (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_id INT,
    page INT, -- page number in the file
    FOREIGN KEY (file_id) REFERENCES Upload(id)
);

CREATE TABLE FilePageChunk (
    id INT PRIMARY KEY AUTO_INCREMENT, -- global id for all chunks regardless of file page they belong to
    page_id INT,
    chunk_id INT, -- chunk's ordering id in the page it belongs to
    FOREIGN KEY (page_id) REFERENCES FilePage(id)
);

```

## Example
```
Upload
-------
id: 8cb1b1f7-aa03-49b9-aea7-ff452f018b2b
filename: Global Hydrogen Review 2024
author: IEA
language: en
date_added: 2025-07-23 03:34:19
size: 10904359
file_type: pdf
source_filename: GlobalHydrogenReview2024.pdf
pages: 0
status: 0
s3_key: 8cb1b1f7-aa03-49b9-aea7-ff452f018b2b/GlobalHydrogenReview2024.pdf
```


```bash
# access Lightsail MySQL via terminal
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH" && source .env && mysql -h $MYSQL_HOST -P 3306 -u $MYSQL_USER -p $MYSQL_DB_NAME

export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH" && source .env && mysql -h $RMI_MYSQL_HOST -P 3306 -u $RMI_MYSQL_USER -p $RMI_MYSQL_DB_NAME
```

# Solution to `uv` Virtual Env Corruption
If ever `.venv/` is corrupted, and you no longer can activate the environment or use command like `uv run <file>`, you can try the following:
1. Delete `.venv`: `rm -rf .venv`
2. Reinstall the environment if you have a `pyproject.toml`: `uv venv`
3. Activate the new environment: `source .venv/bin/activate`

# Connect to Lightsail Instance & Update Code
1. SSH into the instance
2. `cd aws-s3-rds && git pull`
3. Rebuild the Docker image: `cd ~/aws-s3-rds` then, `sudo docker build -t aws-s3-rds:latest .`
4. Restart the Docker container: 
    1. find the current one: `sudo docker ps`
    2. stop/remove it `sudo docker stop <cid> && sudo docker rm <cid>`
    3. run the new image `sudo docker run -d --name aws-s3-rds -p 8000:8000 --env-file .env aws-s3-rds:latest`
5. Verify: `sudo docker ps`

# EXPLANATIOM
## This mini-app accesses 3 AWS services:
1. S3 Bucket: to store actual uploaded files
2. Lightsail Instance (`Ubuntu-*`): host and run this mini uploading app
3. Lightsail Databases (`Database-1`): to store actual metadata of each uploaded file
    - Connection params in `.env`: `RMI_MYSQL_*`
