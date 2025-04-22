# authentication/utils.py
import uuid
import hashlib
import datetime
from bson import ObjectId
from db_connection import users_collection

def hash_password(password):
    """Hash a password for storing."""
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    hash_value, salt = stored_password.split(':')
    return hash_value == hashlib.sha256(salt.encode() + provided_password.encode()).hexdigest()

def create_user(email, password, name, department=None, institution=None, role='teacher'):
    """Create a new user in MongoDB"""
    # Check if user already exists
    if users_collection.find_one({'email': email}):
        return None, 'User with this email already exists'
    
    # Create user document
    user = {
        'email': email,
        'password': hash_password(password),
        'name': name,
        'department': department or '',
        'institution': institution or '',
        'role': role,
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'date_joined': datetime.datetime.now()
    }
    
    # Insert user into MongoDB
    result = users_collection.insert_one(user)
    
    # Return user without password
    user_data = {k: v for k, v in user.items() if k != 'password'}
    user_data['_id'] = str(result.inserted_id)
    
    return user_data, None

def authenticate_user(email, password):
    """Authenticate a user by email and password"""
    user = users_collection.find_one({'email': email})
    
    if not user:
        return None, 'Invalid email or password'
    
    if not verify_password(user['password'], password):
        return None, 'Invalid email or password'
    
    # Return user without password
    user_data = {k: v for k, v in user.items() if k != 'password'}
    user_data['_id'] = str(user_data['_id'])
    
    return user_data, None

# authentication/utils.py
def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        from bson import ObjectId
        print(f"Looking up user with ID: {user_id}")
        
        # Try to convert the user_id to ObjectId
        try:
            object_id = ObjectId(user_id)
        except Exception as e:
            print(f"Error converting user_id to ObjectId: {str(e)}")
            return None
        
        # Find the user
        user = users_collection.find_one({'_id': object_id})
        
        if user:
            # Return user without password
            user_data = {k: v for k, v in user.items() if k != 'password'}
            user_data['_id'] = str(user_data['_id'])
            
            # Convert date_joined to ISO format string if it's a datetime
            if 'date_joined' in user_data and isinstance(user_data['date_joined'], datetime.datetime):
                user_data['date_joined'] = user_data['date_joined'].isoformat()
                
            return user_data
        return None
    except Exception as e:
        print(f"Error in get_user_by_id: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def update_user(user_id, update_data):
    """Update user data"""
    # Don't allow updating email or password through this function
    if 'email' in update_data:
        del update_data['email']
    if 'password' in update_data:
        del update_data['password']
    
    try:
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        # Return updated user
        return get_user_by_id(user_id)
    except:
        return None