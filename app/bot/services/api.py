import logging
from typing import Optional, Dict, Any

import aiohttp
from app.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def post_bitrix_request_aio(endpoint: str, json: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{settings.BITRIX_WEBHOOK}{endpoint}", json=json) as resp:
            print(await resp.json())
            return await resp.json()


# async def post_bitrix_request_aio(
#         endpoint: str,
#         json: dict,
#         timeout: int = 60
# ) -> Optional[Dict[str, Any]]:
#
#
#     url = f"{settings.BITRIX_WEBHOOK}{endpoint}"
#     logger.info(url)
#     logger.info(json)
#
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post(
#                     url,
#                     json=json,
#                     timeout=aiohttp.ClientTimeout(total=timeout)
#             ) as resp:
#                 if resp.status != 200:
#                     error_text = await resp.text()
#                     logger.error(
#                         f"Bitrix API error. Status: {resp.status}. URL: {url}. "
#                         f"Error: {error_text}. Payload: {json}"
#                     )
#                     return None
#
#                 try:
#                     return await resp.json()
#                 except Exception as e:
#                     logger.error(
#                         f"Failed to parse Bitrix response. URL: {url}. "
#                         f"Error: {str(e)}. Response text: {await resp.text()}"
#                     )
#                     return None
#
#     except aiohttp.ClientError as e:
#         logger.error(
#             f"HTTP request to Bitrix failed. URL: {url}. "
#             f"Error: {str(e)}. Payload: {json}"
#         )
#         return None
#     except Exception as e:
#         logger.error(
#             f"Unexpected error during Bitrix request. URL: {url}. "
#             f"Error: {str(e)}. Payload: {json}"
#         )
#         return None