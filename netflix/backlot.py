from netflix.meechum import Meechum
from netflix.service import Service
from functools import wraps

import json
def ensure_session(func):
    @wraps(func)
    def wrapper(self:'Backlot', *args, **kwargs):
        if not self.check_authentication():
            self.logger.debug("Session invalid or expired. Re-authenticating...")
            self.meechum.authenticate(self.redirect_url)
            self.session = self.meechum.session
            self.token = self.get_access_token()
        return func(self, *args, **kwargs)
    return wrapper
class Backlot(Service):
    def __init__(self, meechum: Meechum):
        super().__init__(meechum)
        self.base_url = 'https://backlot.netflixstudios.com'
        self.redirect_url = self.base_url + "/meechum"
        self.authenticated = False
        self.token = None

    def check_authentication(self, refresh_token=False):
        if self.authenticated and not refresh_token:
            return True
        try:
            self.token = self.get_access_token()
            self.logger.debug(self.token)
            self.logger.info("Backlot session is valid, new token requested")
            self.authenticated = True
            return True
        except Exception as e:
            self.logger.warning(f"Backlot session is invalid. Status code: {str(e)}")
            return False
    def get_access_token(self):
        url = f'{self.base_url}/meechum?info=json'
        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if 'access_token' not in data:
            raise Exception("Access token not found in response.")
        return data['access_token']
    @ensure_session
    def search_requests(self, movie_id: str, source_type='SECONDARY_AUDIO_SOURCE'):
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
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def extract_asset_info(self, response_data):
        assets_info = []

        # Assicurati che la chiave 'sr_downloadMaterials' esista nella risposta
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
                    materialFilter = {'language' : language}
                    
                    root_amp_asset = material.get('rootAmpAsset', {})
                    if root_amp_asset:
                        materialFilter["ampAssetId"] = root_amp_asset.get('assetId', {}).get('id')
                    if file_info:
                        if 'location' in file_info and file_info['location'] and 'url' in file_info['location']:
                            materialFilter["fileLocationUrl"] = file_info['location']['url']
                        if 'name' in file_info:
                            materialFilter["fileName"] = file_info['name']
                    if movie_info:
                        materialFilter["movieId"] = movie_info.get('movieId')   
                        
                    asset_info = {
                        'status' : status,
                        'sourceRequestId': source_request_id,
                        'materialType': type,
                        'fileInfo': file_info,
                        'materialFilter': materialFilter
                    }
                    def remove_typename(d):
                        if isinstance(d, dict):
                            return {k: remove_typename(v) for k, v in d.items() if k != '__typename'}
                        elif isinstance(d, list):
                            return [remove_typename(i) for i in d]
                        else:
                            return d

                    asset_info = remove_typename(asset_info)
                    assets_info.append(asset_info)

        return assets_info

    @ensure_session
    def search_download_assets(self, source_request_ids):
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
        query = """
        subscription downloadMaterialsSubscription($sourceRequestIds: [ID!]!) {
          sr_downloadMaterials(sourceRequestIds: $sourceRequestIds) {
            sourceRequestId
            materials {
              ...DownloadableMaterialFields
              __typename
            }
            __typename
          }
        }

        fragment DownloadableMaterialFields on SRMaterial {
          createdDate
          language
          qcStatus
          status
          subType
          type
          videoLanguage
          watermarkState
          audioAmpAsset {
            assetId {
              id
              version
              __typename
            }
            __typename
          }
          rootAmpAsset {
            assetId {
              id
              version
              __typename
            }
            __typename
          }
          ampAsset {
            assetId {
              id
              __typename
            }
            __typename
          }
          downloadRecords {
            downloadAt
            downloadBy
            __typename
          }
          file {
            name
            location {
              url
              __typename
            }
            __typename
          }
          materialType {
            category
            displayName
            type
            __typename
          }
          movie {
            internalTitle
            movieId
            filteredShowHierarchies(filter: VIEW_CURRENT_TITLE) {
              isDefault
              movieId
              movie {
                internalTitle
                movieId
                __typename
              }
              seasonHierarchy {
                movieId
                sequenceNumber
                movie {
                  internalTitle
                  movieId
                  __typename
                }
                episodeHierarchy {
                  movieId
                  parentMovieId
                  sequenceNumber
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
          packageWrapper {
            id
            __typename
          }
          qcRequest {
            qcResult
            result {
              qcCompletedAt
              __typename
            }
            __typename
          }
          __typename
        }
        """
        data = {
            "operationName": "downloadMaterialsSubscription",
            "variables": {
                "sourceRequestIds": source_request_ids
            },
            "query": query
        }
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.startswith('data:'):
                data = json.loads(line[5:])
                if "data" in data and data["data"]:
                    return data["data"]
    @ensure_session
    def download_materials_manifests(self, requests_data):
        url = 'https://studiogateway.prod.netflixstudios.com/subscriptions/sse'
        headers = {
            'accept': 'text/event-stream',
            'authorization': f'Bearer {self.token}',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'pragma': 'no-cache',
            'referer': 'https://backlot.netflixstudios.com/'
        }
        query = """
        subscription downloadMaterialsManifestsSubscription($requests: [SRDownloadMaterialRequest!]!) {
          sr_setupDownloadSessionsForMaterials(requests: $requests) {
            errors {
              message
              material {
                ...DownloadableMaterialFields
                __typename
              }
              __typename
            }
            session {
              asperaBatches {
                asperaHost
                asperaBatchUuid
                asperaTransportToken
                utsUuid
                ... on SRAsperaDownloadBatch {
                  fileDownloads {
                    asperaSource
                    correlationId
                    destinationPath
                    fileIdUuid
                    __typename
                  }
                  __typename
                }
                __typename
              }
              utsUuid
              __typename
            }
            __typename
          }
        }

        fragment DownloadableMaterialFields on SRMaterial {
          createdDate
          language
          qcStatus
          status
          subType
          type
          videoLanguage
          watermarkState
          audioAmpAsset {
            assetId {
              id
              version
              __typename
            }
            __typename
          }
          rootAmpAsset {
            assetId {
              id
              version
              __typename
            }
            __typename
          }
          ampAsset {
            assetId {
              id
              __typename
            }
            __typename
          }
          downloadRecords {
            downloadAt
            downloadBy
            __typename
          }
          file {
            name
            location {
              url
              __typename
            }
            __typename
          }
          materialType {
            category
            displayName
            type
            __typename
          }
          movie {
            internalTitle
            movieId
            filteredShowHierarchies(filter: VIEW_CURRENT_TITLE) {
              isDefault
              movieId
              movie {
                internalTitle
                movieId
                __typename
              }
              seasonHierarchy {
                movieId
                sequenceNumber
                movie {
                  internalTitle
                  movieId
                  __typename
                }
                episodeHierarchy {
                  movieId
                  parentMovieId
                  sequenceNumber
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
          packageWrapper {
            id
            __typename
          }
          qcRequest {
            qcResult
            result {
              qcCompletedAt
              __typename
            }
            __typename
          }
          __typename
        }
        """
        data = {
            "operationName": "downloadMaterialsManifestsSubscription",
            "variables": {
                "requests": requests_data
            },
            "query": query
        }
        response = self.session.post(url, headers=headers, json=data)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.startswith('data:'):
                data = json.loads(line[5:])
                if "data" in data and data["data"]:
                    return data["data"]
