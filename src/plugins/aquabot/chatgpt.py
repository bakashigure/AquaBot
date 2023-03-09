from typing import Callable, List, Optional
import openai
import time
from .utils import Singleton, builtin_cd, async_retry
from .response import *
from loguru import logger


Response = BaseResponse


@Singleton
class ChatBot:
    def __init__(
        self,
        api_key: str,
        max_token: int,
        enable_cd: bool = True,
        cd_function: Optional[Callable] = None,
        cd: int = 10,
        proxy_url = None,
        block_list : List[int] = [],
        context_support : bool = False,
        pro_users: List[int] = []
    ):
        self._api_key = api_key
        self._enable_cd = enable_cd
        self._max_token = max_token
        self._model_name = "gpt-3.5-turbo-0301"
        self._block_list = block_list
        self._cd = cd
        self._context_support = context_support
        self._contexts = {}
        self._pro_users = pro_users
            
        openai.api_key = self._api_key
        if proxy_url:
            openai.proxy = {
                'http': proxy_url,
                'https': proxy_url,
            }
        
        if enable_cd:
            self._cd_function = cd_function if callable(cd_function) else builtin_cd
            self._cd_data = {}

    @async_retry(3, 2, "aqua chat: 出现错误, 请稍后再试")
    async def chat(self, id: int, message: str) -> Response:
        if id in self._block_list:
            return Response(status_code=ACTION_SUCCESS, message="aqua chat: ban!")
        
        if id not in self._pro_users:
            if self._enable_cd and self._cd_function(self._cd_data, id, self._cd):
                return Response(status_code = ACTION_FAILED, message = f"aqua chat: 冷却中, 当前冷却时间为 {self._cd} 秒 ")

        rep = await openai.ChatCompletion.acreate(
            model = self._model_name,
            messages = self.get_query_message(id, message),
            max_tokens = self._max_token,
            temperature = 1
        )
        text = rep['choices'][0]['message']['content'].replace('\\','\\\\').strip()
        
        if self._enable_cd:
            self._cd_data[id] = time.time()

        if self._context_support:
            self._contexts[id].append({"role": "assistant", "content": text})
        return Response(status_code=ACTION_SUCCESS, message=text)

    def reset_chat(self, id):
        if self._context_support and id in self._contexts:
            del self._contexts[id]
            return Response(status_code=ACTION_SUCCESS, message="aqua resetchat: 上下文已重置")
        return Response(status_code=ACTION_FAILED, message="aqua resetchat: 无需重置上下文")
        
    def get_query_message(self, id, message: str):
        if self._context_support:
            if id not in self._contexts:
                self._contexts[id] = [{"role": "user", "content": message}]
                return self._contexts[id]
            else:
                self._contexts[id].append({"role": "user", "content": message})
                return self._contexts[id]
        else:
            return [{"role": "user", "content": message}]
        