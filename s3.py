import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class S3CRUD:
    def __init__(self, bucket_name):
        """
        Initialize S3 client with credentials from environment variables.

        :param bucket_name: Name of the S3 bucket
        """
        logger.info("Initializing S3 client")
        logger.info(os.getenv('AWS_ACCESS_KEY_ID'))
        try:
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name='us-east-1'
            )
            self.bucket_name = bucket_name
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise

    def upload_file(self, file_path, s3_path):
        """
        Upload a file to S3.

        :param file_path: Local file path
        :param s3_path: S3 destination path
        :return: S3 URL if successful, None if failed
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            self.s3.upload_file(file_path, self.bucket_name, s3_path)
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_path}"
            logger.info(f"Successfully uploaded file to {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return None

    def download_file(self, s3_path, local_path):
        """
        Download a file from S3.

        :param s3_path: S3 file path
        :param local_path: Local destination path
        :return: bool indicating success
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, s3_path, local_path)
            logger.info(f"Successfully downloaded file to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return False

    def delete_file(self, s3_path):
        """
        Delete a file from S3.

        :param s3_path: S3 file path
        :return: bool indicating success
        """
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=s3_path)
            logger.info(f"Successfully deleted file: {s3_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False

    def list_files(self, prefix=''):
        """
        List all files in a directory.

        :param prefix: Directory prefix to list
        :return: List of file paths
        """
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except Exception as e:
            logger.error(f"Error listing files from S3: {str(e)}")
            return []

    def get_file_url(self, s3_path):
        """
        Get the public URL for a file.

        :param s3_path: S3 file path
        :return: Public URL string
        """
        return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_path}"


def test_s3_connection():
    """Test S3 connection and basic operations"""
    try:
        s3 = S3CRUD('your-bucket-name')
        # Test listing files
        files = s3.list_files()
        logger.info("S3 connection successful")
        logger.info(f"Files in bucket: {files}")
        return True
    except Exception as e:
        logger.error(f"S3 connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the S3 connection
    test_s3_connection()