from typing import Callable, Optional
import openai
import time
from .utils import Singleton, builtin_cd
from .response import *

Response = BaseResponse


@Singleton
class ChatBot:
    def __init__(
        self,
        organization: str,
        api_key: str,
        max_token: int,
        enable_cd: bool = True,
        cd_function: Optional[Callable] = None,
    ):
        self._organization = organization
        self._api_key = api_key
        self._enable_cd = enable_cd
        self._max_token = max_token
        self._model_name = "gpt-3.5-turbo-0301"

        openai.organization = self._organization
        openai.api_key = self._api_key
        
        if enable_cd:
            self._cd_function = cd_function if callable(cd_function) else builtin_cd
            self._cd_data = {}

    def chat(self, id: int, message: str) -> Response:
        try:
            if self._enable_cd:
                cd = 10
                if self._cd_function(self._cd_data, id, cd):
                    return Response(status_code = ACTION_FAILED, message = f"aqua chat 冷却中, 当前冷却时间为 {cd} 秒 ")
                else:
                    self._cd_data[id] = time.time()

            rep = openai.ChatCompletion.create(
                model = self._model_name,
                messages = [
                    {"role": "user", "content": message}
                ],
                max_tokens = self._max_token,
                temperature = 0.8
            )
            text = rep['choices'][0]['message']['content'].replace('\\','\\\\').strip()
            return Response(status_code=ACTION_SUCCESS, message=text)
        except Exception as e:
            print(e)
            return Response(status_code=ACTION_FAILED, message="aqua chat 发生错误: " + str(e))
        