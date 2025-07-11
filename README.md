# Setup
```bash
# initialize a project in the working directory
$ uv init

# create a virtual env with default name
$ uv venv --python 3.13

# activate the environment
$ source .venv/bin/activate
# automatically activate the virtual environment
Cmd + Shift + P -> Python: Select Interpreter -> type to find .venv

# add dependencies
$ uv add streamlit
$ uv add boto3

```

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