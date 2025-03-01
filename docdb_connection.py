import os
from pymongo.mongo_client import MongoClient
import json
import certifi
import requests
from dotenv import load_dotenv
import datetime

load_dotenv()


def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        print(f"Error getting IP: {e}")
        return None


def connect_to_mongodb():
    # Get MongoDB connection string
    uri = os.getenv("MONGO_DB_KEY")
    if not uri:
        raise ValueError("No MongoDB URI found in environment variables")

    try:
        # First, get and print your public IP
        public_ip = get_public_ip()
        print(f"Your public IP address is: {public_ip}")
        print("Please whitelist this IP in MongoDB Atlas before continuing.")
        input("Press Enter after whitelisting your IP...")

        # Create MongoDB client
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            ssl=True,
            ssl_ca_certs=certifi.where(),
            connect=True,
            connectTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )

        # Test connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        return client

    except Exception as e:
        print(f"Connection error: {str(e)}")
        return None


def main():
    # Get your public IP
    public_ip = get_public_ip()
    if public_ip:
        print(f"\nYour public IP address is: {public_ip}")
        print("\nTo whitelist this IP in MongoDB Atlas:")
        print("1. Go to https://cloud.mongodb.com")
        print("2. Select your project")
        print("3. Click 'Network Access' in the left sidebar")
        print("4. Click '+ ADD IP ADDRESS'")
        print(f"5. Enter your IP: {public_ip}")
        print("6. Click 'Confirm'")

        # Wait for user to whitelist IP
        input("\nPress Enter after whitelisting your IP to continue...")

    # Try to connect to MongoDB
    client = connect_to_mongodb()
    if not client:
        print("Failed to connect to MongoDB")
        return

    try:
        # Test the connection
        db = client['blooger']
        collection = db['summaries']

        # Insert a test document
        test_doc = {
            "test": True,
            "timestamp": datetime.datetime.utcnow(),
            "ip": public_ip
        }

        result = collection.insert_one(test_doc)
        print(f"Successfully inserted test document with ID: {result.inserted_id}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        client.close()


if __name__ == "__main__":
    main()