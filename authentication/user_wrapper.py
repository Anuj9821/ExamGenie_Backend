from django.contrib.auth.models import AnonymousUser

class AuthenticatedMongoUser:
    def __init__(self, mongo_user):
        self.mongo_user = mongo_user
        self._id = mongo_user.get('_id')
        self.email = mongo_user.get('email')
        self.name = mongo_user.get('name')
        self.department = mongo_user.get('department')
        self.institution = mongo_user.get('institution')
        self.role = mongo_user.get('role')
        self.is_active = mongo_user.get('is_active', True)
        self.is_staff = mongo_user.get('is_staff', False)
        self.is_superuser = mongo_user.get('is_superuser', False)
        self.date_joined = mongo_user.get('date_joined')
        
    @property
    def is_authenticated(self):
        # The property to simulate a Django user as authenticated
        return True  # This indicates that the user is authenticated

    def __getattr__(self, attr):
        # Simulating the behavior of Django's User model for missing attributes
        if hasattr(self.mongo_user, attr):
            return getattr(self.mongo_user, attr)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")
