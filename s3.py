import boto3

s3 = boto3.client('s3')
s3.upload_file('C:/Users/Asus-2023/blooogerai/llm_stuff/data/youtube/CF4qM429Brk/screenshots/29.png', 'blooogerai', 'economics_explained.png')

import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError

class S3CRUD:
    def __init__(self, bucket_name, region_name="us-east-1"):
        self.s3 = boto3.client('s3', region_name=region_name)
        self.bucket_name = bucket_name

    def upload_file(self, file_path, s3_path):
        """
        Uploads a file to S3.
        
        :param file_path: Local file path.
        :param s3_path: S3 destination path.
        """
        print("heeeeer")
        try:
            self.s3.upload_file(file_path, self.bucket_name, s3_path)
            print(f"Uploaded {file_path} to {s3_path}")
        except FileNotFoundError:
            print(f"File {file_path} not found.")
        except NoCredentialsError:
            print("Credentials not available.")
        except ClientError as e:
            print(f"ClientError: {e}")

    def download_file(self, s3_path, local_path):
        """
        Downloads a file from S3.
        
        :param s3_path: S3 file path.
        :param local_path: Local destination path.
        """
        try:
            self.s3.download_file(self.bucket_name, s3_path, local_path)
            print(f"Downloaded {s3_path} to {local_path}")
        except ClientError as e:
            print(f"ClientError: {e}")
    
    def list_files(self, prefix):
        """
        List all files under a specific prefix (e.g., vid_id).
        
        :param prefix: S3 folder prefix (e.g., vid_id/).
        :return: List of file paths under the prefix.
        """
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [item['Key'] for item in response['Contents']]
            else:
                return []
        except ClientError as e:
            print(f"ClientError: {e}")
            return []

    def delete_file(self, s3_path):
        """
        Deletes a file from S3.
        
        :param s3_path: S3 file path.
        """
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=s3_path)
            print(f"Deleted {s3_path}")
        except ClientError as e:
            print(f"ClientError: {e}")

    def delete_directory(self, prefix):
        """
        Deletes all files under a specific directory (prefix).
        
        :param prefix: S3 folder prefix (e.g., vid_id/).
        """
        files = self.list_files(prefix)
        for file in files:
            self.delete_file(file)
            print(f"Deleted {file}")

    def update_file(self, file_path, s3_path):
        """
        Updates an existing file by uploading a new version.
        
        :param file_path: Local file path.
        :param s3_path: S3 destination path.
        """
        self.upload_file(file_path, s3_path)
    
    # def create_directory_structure(self, vid_id):
    #     """
    #     Ensures the directory structure exists on S3.
        
    #     :param vid_id: The video ID to create directories for.
    #     """
    #     directories = [
    #         f"{vid_id}/transcript.txt",
    #         f"{vid_id}/screenshots/",
    #         f"{vid_id}/most_replayed.gif"
    #     ]
    #     for directory in directories:
    #         self.s3.put_object(Bucket=self.bucket_name, Key=directory)
    #         print(f"Created placeholder for {directory}")
