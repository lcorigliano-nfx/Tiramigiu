from netflix.meechum import Meechum
from classes.log import Log

class Service:
    def __init__(self, meechum:Meechum):
        self.meechum = meechum
        self.logger = Log().logger
        self.session = meechum.session
        self.headers = meechum.headers.copy()
        self.base_url:str = None
        self.redirect_url:str = None
    def check_authentication(self):
        raise NotImplementedError()
