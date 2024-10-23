from netflix.meechum import Meechum
from classes.log import Log
from functools import wraps
def ensure_session(func):
    @wraps(func)
    def wrapper(self:Service, *args, **kwargs):
        if not self.check_authentication():
            Log().logger.debug("Session invalid or expired. Re-authenticating...")
            self.meechum.authenticate(self.redirect_url)
            self.session = self.meechum.session
        return func(self, *args, **kwargs)
    return wrapper
class Service:
    def __init__(self, meechum:Meechum):
        self.meechum = meechum
        self.session = meechum.session
        self.headers = meechum.headers.copy()
        self.base_url:str = None
        self.redirect_url:str = None
    def check_authentication(self):
        raise NotImplementedError()
