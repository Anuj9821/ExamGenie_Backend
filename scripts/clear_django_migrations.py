import os
import pymongo
import certifi
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB')

def clear_django_migrations():
    client = pymongo.MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
    db = client[MONGODB_DB]
    result = db['django_migrations'].delete_many({})
    print(f"Deleted {result.deleted_count} documents from django_migrations collection.")

if __name__ == "__main__":
    clear_django_migrations()
