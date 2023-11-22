import json
import operator
from typing import Literal
import httpx
from loguru import logger
from .response import *
from io import BytesIO
from .utils import Singleton, builtin_cd, async_retry
import time
import base64

Response=BaseResponse

async def cat_detect(url, img_path, proxies) -> Response:
    """
    识别小猫
    
    Args :
        * ``url: str``: 图片url
        * `` proxies: str``: 代理

    Returns :
        * `` Response.status_code: int`` : 请求的状态码
        * `` Response.content: Image.Image`` : 图片
        * `` Response.message: str`` : 请求失败的原因
    """

    _retry = 3
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxies) as client:
                file = {'file':open(img_path, 'rb')}
                res = await client.post(url, files=file, timeout=5)
                res_json = res.json()
                if 'img' in res_json:
                    img_data = res_json.get('img')
                    img_data = base64.b64decode(img_data)
                    return Response(ACTION_SUCCESS, content=BytesIO(img_data))
                else:
                    return Response(ACTION_FAILED, content="")

        except Exception as e:
            print(e)
            _retry -= 1
            if _retry == 0:
                return Response(ACTION_FAILED, message="下载图片出现错误, 请稍后再试")