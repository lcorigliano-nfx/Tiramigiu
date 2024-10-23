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

logger.info("Ending the application")
