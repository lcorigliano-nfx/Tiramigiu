import sys
from netflix.meechum import Meechum
from netflix.backlot import Backlot
from classes.log import Log
from classes.aspera import Aspera
# Example usage
logger = Log().logger

logger.info("Starting the application")

meechum = Meechum()
backlot = Backlot(meechum)
search_response = backlot.search_requests(movie_id="81635402")

if 'sourceRequest' in search_response:
    logger.info("sourceRequest found in search_response")
    # Estrai tutti i requestId
    request_ids = [request['requestId'] for request in search_response['sourceRequest']]
    logger.debug(f"Extracted request IDs: {request_ids}")
else:
    logger.error("sourceRequest not found in search_response")
    sys.exit(1)
import json
assets = backlot.search_download_assets(request_ids)
with open('assets.json', 'w') as f:
    json.dump(assets, f, indent=4)
assets = backlot.extract_asset_info(assets)
with open('assets_processed.json', 'w') as f:
    json.dump(assets, f, indent=4)

available_assets = []
for asset in assets:
    if asset['status'] == 'ACTIVE':
        for type in ['PRINT_MASTER', 'DIALOGUE_LIST', 'LOCKED_PROXY',  'DIALOG_MUSIC_AND_EFFECTS', 'MIX_MINUS' ]: 
            if type in asset['materialType']:
                available_assets.append(asset)
                break
# Remove the 'status' field from the assets
for asset in available_assets:
    if 'status' in asset:
        del asset['status']
    if 'fileInfo' in asset:
        del asset['fileInfo']
    if 'fileName' in asset['materialFilter']:
        del asset['materialFilter']['fileName']

aspera_manifests = backlot.download_materials_manifests(available_assets)
if "sr_setupDownloadSessionsForMaterials" in aspera_manifests:
    aspera_manifests = aspera_manifests["sr_setupDownloadSessionsForMaterials"]
    with open('aspera_manifests.json', 'w') as f:
        json.dump(aspera_manifests, f, indent=4)
    for session in aspera_manifests["session"]:
        for batch in session["asperaBatches"]:
            aspera = Aspera(batch)
            aspera.start_batch_download()