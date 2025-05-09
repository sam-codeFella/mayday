import boto3
from dotenv import load_dotenv
load_dotenv() # to load all the env variables exposed from .env file.

s3_client = boto3.client('s3')

# List buckets
def print_buckets():
    response = s3_client.list_buckets()
    print([bucket['Name'] for bucket in response['Buckets']])

if __name__=="__main__":
    print_buckets()