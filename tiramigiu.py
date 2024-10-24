import sys
import json
import requests
from netflix.meechum import Meechum
from netflix.backlot import Backlot
from classes.log import Log
from classes.aspera import Aspera

class Tiramigiu:
    def __init__(self):
        self.logger = Log().get_logger(self.__class__.__name__)
        self.meechum = Meechum()
        self.backlot = Backlot(self.meechum)

    # Slack notification function
    def send_slack_notification(self, message):
        return
        webhook_url = 'YOUR_SLACK_WEBHOOK_URL'
        payload = {'text': message}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        if response.status_code != 200:
            self.logger.error(f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}")

    def process_movie_ids(self, movie_ids):
        for movie_id in movie_ids:
            self.logger.info(f"Processing movie ID: {movie_id}")
            search_response = self.backlot.search_requests(movie_id=movie_id)

            if 'sourceRequest' in search_response:
                self.logger.info("sourceRequest found in search_response")
                # Extract all requestIds
                request_ids = [request['requestId'] for request in search_response['sourceRequest']]
                self.logger.debug(f"Extracted request IDs: {request_ids}")
                if len(request_ids) == 0:
                    self.logger.error("No request IDs found in search_response")
                    self.send_slack_notification(f"No sourceRequest found for movie ID: {movie_id}")
                    continue
            else:
                self.logger.error("sourceRequest not found in search_response")
                self.send_slack_notification(f"Failed to find sourceRequest for movie ID: {movie_id}")
                continue

            assets = self.backlot.search_download_assets(request_ids)
            with open(f'assets_{movie_id}.json', 'w') as f:
                json.dump(assets, f, indent=4)
            assets = self.backlot.extract_asset_info(assets)
            with open(f'assets_processed_{movie_id}.json', 'w') as f:
                json.dump(assets, f, indent=4)

            usable_assets = []
            available_assets = []
            seen_files = set()
            for asset in assets:
                if asset['status'] == 'ACTIVE':
                    if 'materialFilter' in asset and 'fileName' in asset['materialFilter']:
                        fileName = asset['materialFilter']['fileName']
                        if fileName not in seen_files:
                            available_assets.append(asset)
                            seen_files.add(fileName)
            with open(f'assets_available_{movie_id}.json', 'w') as f:
                json.dump(available_assets, f, indent=4)
            categorized_assets = {
                'FINAL_PROXY': [],
                'LOCKED_PROXY': [],
                'PROXY_WITH_SUBTITLES': [],
                'SERVICING_PROXY': [],
                'DIALOGUE_LIST': [],
                'PIVOT_LANGUAGE_DIALOGUE_LIST': [],
                'PRINT_MASTER_5_1_CH': [],
                'PRINT_MASTER_2_0_CH': [],
                'DIALOG_MUSIC_AND_EFFECTS_5_1_CH': [],
                'DIALOG_MUSIC_AND_EFFECTS_2_0_CH': []
            }

            for asset in available_assets:
                material_type = asset['materialType']
                if 'FINAL_PROXY' in material_type:
                    categorized_assets['FINAL_PROXY'].append(asset)
                elif 'PROXY_WITH_SUBTITLES' in material_type:
                    categorized_assets['PROXY_WITH_SUBTITLES'].append(asset)
                elif 'LOCKED_PROXY' in material_type:
                    categorized_assets['LOCKED_PROXY'].append(asset)
                elif 'SERVICING_PROXY' in material_type:
                    categorized_assets['SERVICING_PROXY'].append(asset)
                elif 'DIALOGUE_LIST' in material_type:
                    categorized_assets['DIALOGUE_LIST'].append(asset)
                elif 'PIVOT_LANGUAGE_DIALOGUE_LIST' in material_type:
                    categorized_assets['PIVOT_LANGUAGE_DIALOGUE_LIST'].append(asset)
                elif 'PRINT_MASTER' in material_type:
                    if '5_1_CH' in material_type:
                        categorized_assets['PRINT_MASTER_5_1_CH'].append(asset)
                    elif '2_0_CH' in material_type:
                        categorized_assets['PRINT_MASTER_2_0_CH'].append(asset)
                elif 'DIALOG_MUSIC_AND_EFFECTS' in material_type:
                    if '5_1_CH' in material_type:
                        categorized_assets['DIALOG_MUSIC_AND_EFFECTS_5_1_CH'].append(asset)
                    elif '2_0_CH' in material_type:
                        categorized_assets['DIALOG_MUSIC_AND_EFFECTS_2_0_CH'].append(asset)
            for category, assets in categorized_assets.items():
                self.logger.debug(f"Category: {category}, Count: {len(assets)}")
            # Select the best available assets
            usable_assets.extend(categorized_assets['FINAL_PROXY'] or categorized_assets['PROXY_WITH_SUBTITLES'] or categorized_assets['LOCKED_PROXY'] or categorized_assets['SERVICING_PROXY'])
            usable_assets.extend(categorized_assets['DIALOGUE_LIST'])
            usable_assets.extend(categorized_assets['PIVOT_LANGUAGE_DIALOGUE_LIST'])
            usable_assets.extend(categorized_assets['PRINT_MASTER_5_1_CH'] or categorized_assets['PRINT_MASTER_2_0_CH'])
            usable_assets.extend(categorized_assets['DIALOG_MUSIC_AND_EFFECTS_5_1_CH'] or categorized_assets['DIALOG_MUSIC_AND_EFFECTS_2_0_CH'])
            # Remove the 'status' field from the assets
            for asset in usable_assets:
                if 'status' in asset:
                    del asset['status']
                if 'fileInfo' in asset:
                    del asset['fileInfo']
                if 'fileName' in asset['materialFilter']:
                    del asset['materialFilter']['fileName']
            with open(f'categorized_assets_{movie_id}.json', 'w') as f:
                json.dump(usable_assets, f, indent=4)
            aspera_manifests = self.backlot.download_materials_manifests(usable_assets)
            if "sr_setupDownloadSessionsForMaterials" in aspera_manifests:
                aspera_manifests = aspera_manifests["sr_setupDownloadSessionsForMaterials"]
                with open(f'aspera_manifests_{movie_id}.json', 'w') as f:
                    json.dump(aspera_manifests, f, indent=4)
                for session in aspera_manifests["session"]:
                    for batch in session["asperaBatches"]:
                        aspera = Aspera(batch, download_folder=f"/Volumes/mne-qc/downloads/Tiramigiu/", movie_id=movie_id)
                        aspera.start_batch_download()
                self.send_slack_notification(f"Successfully downloaded materials for movie ID: {movie_id}")
            else:
                self.send_slack_notification(f"Failed to download materials for movie ID: {movie_id}")

if __name__ == "__main__":
    # Entry point
    if len(sys.argv) > 1:
        movie_ids = sys.argv[1:]
    else:
        print("Usage: python tiramigiu.py <movie_id1> <movie_id2> ...")
        sys.exit(1)

    tiramigiu = Tiramigiu()
    tiramigiu.process_movie_ids(movie_ids)