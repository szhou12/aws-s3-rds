# Setup
```bash
# initialize a project in the working directory
$ uv init

# create a virtual env with default name
$ uv venv --python 3.13

# activate the environment
$ source .venv/bin/activate

# add dependencies
$ uv add streamlit

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