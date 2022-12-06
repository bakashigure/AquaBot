# Code from https://github.com/A-kirami/nonebot-plugin-chatgpt/blob/master/nonebot_plugin_chatgpt/chatgpt.py

import uuid
from typing import Any, Dict, Optional

import httpx
from nonebot.log import logger

from nonebot.exception import NetworkError

from .config import Config, _config

try:
    import ujson as json
except ModuleNotFoundError:
    import json

SESSION_TOKEN = "__Secure-next-auth.session-token"


class Chatbot:
    def __init__(self) -> None:
        self.session_token = _config['chatgpt_session_token']
        self.authorization = None

    def __call__(
        self, conversation_id: Optional[str] = None, parent_id: Optional[str] = None
    ):
        self.conversation_id = conversation_id
        self.parent_id = parent_id or self.id
        return self

    @property
    def id(self) -> str:
        return str(uuid.uuid4())

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.authorization}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        }

    def reset_chat(self) -> None:
        self.conversation_id = None
        self.parent_id = self.id

    def get_payload(self, prompt: str) -> Dict[str, Any]:
        return {
            "action": "next",
            "messages": [
                {
                    "id": self.id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [prompt]},
                }
            ],
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_id,
            "model": "text-davinci-002-render",
        }

    async def get_chat_response(self, prompt: str, proxies = None) -> str:
        if not self.authorization:
            await self.refresh_session(proxies=proxies)
        async with httpx.AsyncClient(proxies=proxies) as client:
            retry_times = 0
            while retry_times < 2:
                try:
                    response = await client.post(
                    "https://chat.openai.com/backend-api/conversation",
                    headers=self.headers,
                    json=self.get_payload(prompt),
                    timeout=20,
                    )
                    response = response.text.splitlines()[-4]
                    response = response[6:]
                    response = json.loads(response)
                    self.parent_id = response["message"]["id"]
                    self.conversation_id = response["conversation_id"]
                    return response["message"]["content"]["parts"][0]
                except Exception as e:
                    logger.error(e)
                    retry_times += 1

    async def refresh_session(self, proxies = None) -> None:
        cookies = {SESSION_TOKEN: self.session_token}
        async with httpx.AsyncClient(
            cookies=cookies,
            proxies=proxies,  # type: ignore
            timeout=10,
        ) as client:
            response = await client.get("https://chat.openai.com/api/auth/session",
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
                },)
        try:
            self.session_token = response.cookies.get(SESSION_TOKEN, "")  # type: ignore
            self.authorization = response.json()["accessToken"]
        except Exception as e:
            raise RuntimeError("Error refreshing session") from e