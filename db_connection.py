# db_connection.py
import os
import pymongo
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment variables
url = os.getenv('MONGODB_URI')
db_name = os.getenv('MONGODB_DB', 'examgenie_database')

try:
    # Connect to MongoDB with SSL certificate
    client = pymongo.MongoClient(
        url,
        tlsCAFile=certifi.where(),
        connectTimeoutMS=30000,
        socketTimeoutMS=None,
        connect=False,
        maxPoolSize=50
    )
    
    # Test connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
    # Access the database with explicit name
    db = client[db_name]
    
    # Define collections
    users_collection = db['users']
    question_banks_collection = db['question_banks']
    papers_collection = db['papers']
    profiles_collection = db['profiles']
    
    # Create indexes only if collections exist
    if 'users' in db.list_collection_names():
        if 'email_1' not in [idx.get('name') for idx in list(users_collection.list_indexes())]:
            users_collection.create_index('email', unique=True)
    
    if 'question_banks' in db.list_collection_names():
        if 'subject_name_1' not in [idx.get('name') for idx in list(question_banks_collection.list_indexes())]:
            question_banks_collection.create_index('subject_name')
    
    if 'papers' in db.list_collection_names():
        if 'created_at_1' not in [idx.get('name') for idx in list(papers_collection.list_indexes())]:
            papers_collection.create_index('created_at')
    
except Exception as e:
    print(f"MongoDB Error: {e}")
    # Create dummy collections for development if connection fails
    class DummyCollection:
        def __init__(self, name):
            self.name = name
            self._data = []
        
        def insert_one(self, document):
            document['_id'] = str(len(self._data) + 1)
            self._data.append(document)
            return type('obj', (object,), {'inserted_id': document['_id']})
        
        def find_one(self, query):
            for doc in self._data:
                match = True
                for k, v in query.items():
                    if k not in doc or doc[k] != v:
                        match = False
                        break
                if match:
                    return doc
            return None
        
        def find(self, query=None):
            if query is None:
                return self._data
            results = []
            for doc in self._data:
                match = True
                for k, v in query.items():
                    if k not in doc or doc[k] != v:
                        match = False
                        break
                if match:
                    results.append(doc)
            return results
        
        def update_one(self, query, update):
            for doc in self._data:
                match = True
                for k, v in query.items():
                    if k not in doc or doc[k] != v:
                        match = False
                        break
                if match:
                    for k, v in update.get('$set', {}).items():
                        doc[k] = v
                    return
        
        def create_index(self, field, unique=False):
            pass
        
        def list_indexes(self):
            return []
        
        def delete_many(self, query):
            count = 0
            new_data = []
            for doc in self._data:
                match = True
                for k, v in query.items():
                    if k not in doc or doc[k] != v:
                        match = False
                        break
                if not match:
                    new_data.append(doc)
                else:
                    count += 1
            self._data = new_data
            return type('obj', (object,), {'deleted_count': count})
    
    # Create dummy collections
    db = type('obj', (object,), {'list_collection_names': lambda: []})
    users_collection = DummyCollection('users')
    question_banks_collection = DummyCollection('question_banks')
    papers_collection = DummyCollection('papers')
    profiles_collection = DummyCollection('profiles')
    print("Using in-memory collections for development")