import os
import boto3

BUCKET_NAME = 'rag-file-storage-bucket'

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

# Show all buckets created
response = s3_client.list_buckets()
for bucket in response['Buckets']:
    print(bucket)


# Show all objects stored in a bucket
response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
objects = response.get('Contents', [])
print(f"{len(objects)} objects found: {objects}")

# Download a file from s3 bucket
s3_client.download_file(
    Bucket=BUCKET_NAME,
    Key='file1.txt', # file name in s3 bucket
    Filename='downloaded_file1.txt' # give a file name downloaded to local
)

# Enable a bucket's versioning - allow storing multiple files with the same name
s3_client.put_bucket_versioning(
    Bucket=BUCKET_NAME,
    VersioningConfiguration={
        'Status': 'Enabled'
    }
)

response = s3_client.list_object_versions(
    Bucket=BUCKET_NAME,
    Prefix='file1.txt'
)

for version in response['Versions']:
    print(version)

s3_client.download_file(
    Bucket=BUCKET_NAME,
    Key='file1.txt',
    Filename='downloaded_file1_v1.txt',
    ExtraArgs={
        'VersionId': 'null'
    }
)

s3_client.download_file(
    Bucket=BUCKET_NAME,
    Key='file1.txt',
    Filename='downloaded_file1_v2.txt',
    ExtraArgs={
        'VersionId': 'assigned_version_id'
    }
)

s3_client.upload_file(
    Filename='file1.txt', # file name in local that you wish to upload to s3
    Bucket=BUCKET_NAME,
    Key='file1.txt', # this file's filename in s3 bucket
    ExtraArgs={
        'ContentType': 'text/plain', # file type
    }
)

# Delete a file from s3 bucket
s3_client.delete_object(
    Bucket=BUCKET_NAME,
    Key='file1.txt'
)

# Empty a bucket
bucket = s3_resource.Bucket(BUCKET_NAME)
bucket.objects.all().delete() # delete all objects in the bucket
bucket.object_versions.all().delete() # delete all versions of the objects in the bucket

# Delete a bucket
s3_client.delete_bucket(Bucket=BUCKET_NAME)

# Create a bucket with a lifecycle policy
s3_client.create_bucket(
    Bucket=BUCKET_NAME,
    CreateBucketConfiguration={
        'LocationConstraint': 'us-east-1'
    }
)

