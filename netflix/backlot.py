from netflix.meechum import Meechum
from netflix.service import Service
from functools import wraps
import json
from classes.log import Log
from typing import List, Dict, Any, Optional

def ensure_session(func):
  @wraps(func)
  def wrapper(self: 'Backlot', *args, **kwargs):
    if not self.check_authentication():
      self.logger.debug("Session invalid or expired. Re-authenticating...")
      self.meechum.authenticate(self.redirect_url)
      self.session = self.meechum.session
      self.token = self.get_access_token()
    return func(self, *args, **kwargs)
  return wrapper

class Backlot(Service):
  DOWNLOAD_MATERIALS_QUERY: Optional[str] = None
  DOWNLOAD_MATERIALS_MANIFESTS_QUERY: Optional[str] = None

  def __init__(self, meechum: Meechum):
    super().__init__(meechum)
    self.base_url = 'https://backlot.netflixstudios.com'
    self.redirect_url = self.base_url + "/meechum"
    self.logger = Log().get_logger(self.__class__.__name__)
    
    # Load GraphQL queries from files
    try:
      with open('graphql/downloadMaterials.graphql', 'r') as f:
        self.DOWNLOAD_MATERIALS_QUERY = f.read()
      with open('graphql/downloadMaterialsManifests.graphql', 'r') as f:
        self.DOWNLOAD_MATERIALS_MANIFESTS_QUERY = f.read()
    except FileNotFoundError as e:
      self.logger.error(f"GraphQL query file not found: {e}")
      raise
    except Exception as e:
      self.logger.error(f"Error loading GraphQL query files: {e}")
      raise
    
    self.authenticated = False
    self.token = None

  def check_authentication(self, refresh_token: bool = False) -> bool:
    """Check if the current session is authenticated."""
    if self.authenticated and not refresh_token:
      return True
    try:
      self.token = self.get_access_token()
      self.logger.debug(f"Access token: {self.token}")
      self.logger.info("Backlot session is valid, new token requested")
      self.authenticated = True
      return True
    except Exception as e:
      self.logger.warning(f"Backlot session is invalid. Status code: {str(e)}")
      return False

  def get_access_token(self) -> str:
    """Retrieve the access token from the Meechum service."""
    url = f'{self.base_url}/meechum?info=json'
    try:
      response = self.session.get(url, headers=self.headers)
      response.raise_for_status()
      data = response.json()
      if 'access_token' not in data:
        raise Exception("Access token not found in response.")
      return data['access_token']
    except Exception as e:
      self.logger.error(f"Failed to get access token: {e}")
      raise

  @ensure_session
  def search_requests(self, movie_id: str, source_type: str = 'SECONDARY_AUDIO_SOURCE') -> Dict[str, Any]:
    """Search for source requests based on movie ID and source type."""
    url = f'{self.base_url}/api/sourceRequests'
    headers = self.headers.copy()
    headers.update({
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
    try:
      response = self.session.post(url, headers=headers, json=data)
      response.raise_for_status()
      return response.json()
    except Exception as e:
      self.logger.error(f"Failed to search requests: {e}")
      raise

  def extract_asset_info(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract asset information from the response data."""
    assets_info = []

    if 'sr_downloadMaterials' in response_data:
      for item in response_data['sr_downloadMaterials']:
        source_request_id = item.get('sourceRequestId')
        materials = item.get('materials', [])

        for material in materials:
          status = material.get('status', 'UNKNOWN')
          file_info = material.get('file', {})
          movie_info = material.get('movie', {})
          type = material.get('type', 'UNKNOWN')
          language = material.get('language', None)
          material_filter = {}

          root_amp_asset = material.get('rootAmpAsset', {})
          if root_amp_asset:
            material_filter["ampAssetId"] = root_amp_asset.get('assetId', {}).get('id')
          if file_info:
            if 'location' in file_info and file_info['location'] and 'url' in file_info['location']:
              material_filter["fileLocationUrl"] = file_info['location']['url']
            if 'name' in file_info:
              material_filter["fileName"] = file_info['name']
          if movie_info:
            material_filter["movieId"] = movie_info.get('movieId')

          asset_info = {
            'status': status,
            'language': language,
            'sourceRequestId': source_request_id,
            'materialType': type,
            'fileInfo': file_info,
            'materialFilter': material_filter
          }
          assets_info.append(asset_info)

    return assets_info

  @ensure_session
  def search_download_assets(self, source_request_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Search for download assets based on source request IDs."""
    url = 'https://studiogateway.prod.netflixstudios.com/subscriptions/sse'
    headers = {
      'accept': 'text/event-stream',
      'authorization': f'Bearer {self.token}',
      'cache-control': 'no-cache',
      'content-type': 'application/json',
      'origin': 'https://backlot.netflixstudios.com',
      'pragma': 'no-cache',
      'referer': 'https://backlot.netflixstudios.com/'
    }
    data = {
      "operationName": "downloadMaterialsSubscription",
      "variables": {
        "sourceRequestIds": source_request_ids
      },
      "query": self.DOWNLOAD_MATERIALS_QUERY
    }
    try:
      response = self.session.post(url, headers=headers, json=data)
      response.raise_for_status()
      for line in response.text.splitlines():
        if line.startswith('data:'):
          data = json.loads(line[5:])
          if "data" in data and data["data"]:
            return data["data"]
      return None
    except Exception as e:
      self.logger.error(f"Failed to search download assets: {e}")
      raise

  @ensure_session
  def download_materials_manifests(self, requests_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Download materials manifests based on request data."""
    url = 'https://studiogateway.prod.netflixstudios.com/subscriptions/sse'
    headers = {
      'accept': 'text/event-stream',
      'authorization': f'Bearer {self.token}',
      'cache-control': 'no-cache',
      'content-type': 'application/json',
      'pragma': 'no-cache',
      'referer': 'https://backlot.netflixstudios.com/'
    }
    data = {
      "operationName": "downloadMaterialsManifestsSubscription",
      "variables": {
        "requests": requests_data
      },
      "query": self.DOWNLOAD_MATERIALS_MANIFESTS_QUERY
    }
    try:
      response = self.session.post(url, headers=headers, json=data)
      response.raise_for_status()
      for line in response.text.splitlines():
        if line.startswith('data:'):
          data = json.loads(line[5:])
          if "data" in data and data["data"]:
            return data["data"]
      raise Exception("No data found in response")
    except Exception as e:
      self.logger.error(f"Failed to download materials manifests: {e}")
      raise
