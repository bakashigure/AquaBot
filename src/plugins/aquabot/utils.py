"""
Define some functions for AquaBot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from io import BytesIO
from pathlib import Path
import json
from typing import Literal
import nonebot
from nonebot import logger
from PIL import Image
from nonebot.adapters.cqhttp import message
import oss2
import httpx
from .config import _config
from time import time
from os.path import getsize as _getsize
from .response import *

logger.warning("IMPORT UTILS")
__version__ = "0.0.1"

global_config = nonebot.get_driver().config

class Response(BaseResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if status := self.status_code // 100 == 2:
            logger.info(self.log)
        elif status == 3:
            logger.warning(self.log)
        else:
            logger.error(self.log)


def _get_bot(bot_id):
    """
    返回一个bot实例

    Args :
        >>> bot_id(int): bot的qq号

    Returns :
          >>> bot(nonebot.adapters.cqhttp.bot.Bot): bot实例
    """
    try:
        logger.warning(nonebot.get_bots())
        bot = nonebot.get_bots()[str(bot_id)]
        return bot
    except KeyError:
        logger.error("bot'%s'未连接" % bot_id)


async def get_message_image(data: str, type: Literal["file", "url"]) -> list:
    """
    返回一个包含消息中所有图片文件的list, 

    Args : 
          >>> data(str): 消息内容, 来自event.json()
          >>> type('file'): 返回文件名, 需搭配cqhttp客户端的data文件夹获取本地图片(推荐)
          >>> type('url') : 返回图片url, 有概率获取到腾讯禁止爬虫页面导致获取图片失败  
          >>> path(str): 当type为'file'时需指定cqhttp的data文件夹

    Return :
          >>> list: 包含图片绝对路径或url的list
    """
    _img_list = []
    path = global_config.cqhttp
    _data = json.loads(data)
    bot = _get_bot(_data["self_id"])
    for message in _data["message"]:
        if message["type"] == "image":
            if type == "file":
                _file_detail = await bot.get_image(file=message["data"][type])
                _path = path + "/" + str(_file_detail["file"])
                # TODO add linux file system
                _img_list.append(_path)
            else:
                _img_list.append(message["data"][type])

    return _img_list


def get_message_text(data: str) -> str:
    """
    返回消息纯文本
    """
    pass


def _clear_cache():
    ...


def _resize_image(origin: str, max_size: int, k: float) -> Image.Image:
    """接受一个图片, 将其转换为jpg, 大小不超过max_size,
    过程中产生的临时文件存储于_config['cache']下

    Args :
        >>> file(str): 源图片目录
        >>> max_size(int): 最大大小, 单位为KB
        >>> k(float): 每次缩小分辨率的比值

    Returns :
        >>> image(Image.Image): 处理后的图片对象
    """
    _max_size = max_size * 1024  # convert KB to Bytes
    im = Image.open(origin)
    (x, y) = im.size
    if im.format == "gif":
        return im
    else:
        tmp_fp = (lambda: _config["cache"] + "/" + str(time.time()).replace(".", "") + ".jpg")
        _tmp = tmp_fp()
        im.save(_tmp)

        if _getsize(_tmp) > _max_size:
            while True:
                _tmp = tmp_fp()
                (x, y) = (x * k, y * k)
                _out = im.resize((x, y))
                _out.save(_tmp)
                _out.close()
                if _getsize(_tmp < _max_size):
                    im.close()
                    return _tmp
        else:
            im.close()
            return _tmp


async def _upload_custom(
    origin: str, target: str, target_filename: str, max_size: int = 4096
):
    """Upload函数

    Args ::
        >>> origin(str): 源文件地址
        >>> targer(str): 目标路径
        >>> target_filename(str): 目标文件名
        >>> max_size(int): 最大文件大小, 大于的直接进行一个压缩 
    """
    if _config["storage"] == "local":
        _origin = _resize_image(file=origin, max_size=max_size, k=0.9)
        _origin.save(target + "/" + target_filename)
        _origin.close()

    else:
        oss2.Bucket.put_object
        ...

def upload_to_local(origin: str, target: str, target_filename: str, max_size: int = 4096):
    """上传文件到本地

    Args :
        >>> origin(str): 源文件地址
        >>> targer(str): 目标路径
        >>> target_filename(str): 目标文件名
        >>> max_size(int): 最大文件大小, 大于的直接进行一个压缩 
    """
    _origin = _resize_image(file=origin, max_size=max_size, k=0.9)
    _origin.save(target + "/" + target_filename)
    _origin.close()


async def _aio_upload_oss():
    ...


async def __make_sign():
    ...


async def _safe_send(id: int, api: str, **message):
    bot = _get_bot(id)
    try:
        await bot.call_api(api, message)
    except Exception as e:
        logger.error("fail to send message, error %s" % e)


def get_path(path):
    return Path(path).resolve()


async def _safe_get_image(url: str, headers: dict = None, proxies: str = None) -> Response:
    """
    下载图片, 并返回图片对象

    Args :
        >>> url(str): 图片url
        >>> headers(dict): 请求头
        >>> proxies(str): 代理
    Returns :
        >>> Response.status_code(int): 请求的状态码
        >>> Response.content(Image.Image): 图片
        >>> Response.message(str): 请求失败的原因
    """
    try:
        async with httpx.AsyncClient(proxies=proxies) as client:
            res = await client.get(url, headers=headers, timeout=5)
            res.raise_for_status()
    except httpx.ProxyError as exc:
        return Response(ACTION_FAILED,message="httpx proxy error.")
    except httpx.HTTPStatusError as exc:
        return Response(ACTION_FAILED,message=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
    return Response(ACTION_SUCCESS, content=BytesIO(res.content))


async def get_pixiv_image(url: str, proxies=None) -> Response:
    """
    下载一张pixiv图片, 会带上pixiv请求头, 返回图片对象

    Args :
        >>> url(str): 图片url
        >>> proxies(str): 代理(可选)

    Returns:
        >>> Response.status_code(int): 请求的状态码
        >>> Response.content(Image.Image): 图片
        >>> Response.message(str): 请求失败的原因
    """
    headers = {"Referer": "https://www.pixiv.net/"}
    return await _safe_get_image(url, headers=headers, proxies=proxies)
