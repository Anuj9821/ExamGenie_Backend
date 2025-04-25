# authentication/user_wrapper.py

class AuthenticatedMongoUser:
    def __init__(self, user_data):
        self.user_data = user_data

    def __getattr__(self, item):
        return self.user_data.get(item)

    @property
    def is_authenticated(self):
        return True
