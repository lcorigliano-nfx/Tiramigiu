from netflix.meechum import Meechum
from netflix.service import Service, ensure_session
from classes.log import Log


class Backlot(Service):
    def __init__(self, meechum: Meechum):
        super().__init__(meechum)
        self.base_url = 'https://backlot.netflixstudios.com'
        self.redirect_url = self.base_url + "/meechum"
        self.logger = Log().logger

    def check_authentication(self):
        url = self.base_url + '/meechum?info=json'
        response = self.session.get(url)
        if response.status_code == 200:
            self.logger.info("Backlot session is valid.")
            return True
        else:
            self.logger.error(f"Backlot session is invalid. Status code: {response.status_code}")
            return False

    @ensure_session
    def search_requests(self, movie_id: str, source_type='SECONDARY_AUDIO_SOURCE'):
        url = f'{self.base_url}/api/sourceRequests'
        self.headers.update({
            'content-type': 'application/json',
            'origin': self.base_url,
            'x-requested-with': 'XMLHttpRequest'
        })
        data = {
            "dataset": {
                "and": [
                    {"or": [{"field": "requestStatus", "eq": "all"}]},
                    {"or": [{"field": "movieIds", "eq": movie_id}]},
                    {"or": [{"field": "sourceType", "eq": source_type}]}
                ]
            },
            "queryConfig": {
                "start": 0,
                "limit": 25000,
                "includeAllFields": False
            }
        }
        response = self.session.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
