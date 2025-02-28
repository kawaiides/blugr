
from pymongo.mongo_client import MongoClient
import json

uri = "mongodb+srv://shyamthegoodboy:5sBOzYYOqg3V5PAO@blooogerai.spz14.mongodb.net/?retryWrites=true&w=majority&appName=blooogerai"

# Create a new client and connect to the server
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    db = client['test']
    collection = db['summaries']
    with open(f"./data/youtube/CF4qM429Brk/summary.json", "r") as f:
        data = json.load(f)
    collection.insert_one(data)
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)