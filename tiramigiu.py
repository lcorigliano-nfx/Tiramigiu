import sys
from netflix.meechum import Meechum
from netflix.backlot import Backlot
from classes.log import Log
# Example usage
logger = Log().logger

logger.info("Starting the application")

meechum = Meechum()
backlot = Backlot(meechum)
search_response = backlot.search_requests(movie_id="81710698")

if 'sourceRequest' in search_response:
    logger.info("sourceRequest found in search_response")
    # Estrai tutti i requestId
    request_ids = [request['requestId'] for request in search_response['sourceRequest']]
    logger.debug(f"Extracted request IDs: {request_ids}")
else:
    logger.error("sourceRequest not found in search_response")
    sys.exit(1)
import json

assets = backlot.extract_asset_info(backlot.search_download_assets(request_ids))
with open('assets_processed.json', 'w') as f:
    json.dump(assets, f, indent=4)
sys.exit(0)
assets = backlot.extract_asset_info()
available_assets = [asset for asset in assets if asset['status'] == 'ACTIVE']
logger.info("Ending the application")
