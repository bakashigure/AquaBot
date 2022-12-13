# @Author: bakashigure 
# @Date: 2022-01-31 17:29:03 
# @Last Modified by:   bakashigure 
# @Last Modified time: 2022-01-31 17:29:03 

"""
Define some functions for AquaBot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from io import BytesIO
from pathlib import Path
import json
from typing import Literal,Union
import nonebot
from nonebot.log import logger
from PIL import Image
from nonebot.adapters.onebot.v11 import message
import oss2
import httpx
from .config import _config
import time
from os.path import getsize
from .response import *

logger.warning("importing utils...")

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
        ``bot_id: int`` :bot的qq号

    Returns :
        ``bot: nonebot.adapters.cqhttp.bot.Bot)`` :bot实例
    """
    return nonebot.get_bots()[str(bot_id)]



async def get_message_image(data, type: Literal["file", "url"]) -> list:
    """
    返回一个包含消息中所有图片文件路径的list, 

    Args : 
          * ``data: str`` : 消息内容, 来自event.json()  
          * ``type: Literal['file','url']``: 当``type``为``'file'``时, 返回的是文件路径, 当``type``为``'url'``时, 返回的是url  

    Return :
          * ``_img_list: list`` : 包含图片绝对路径或url的list
    """
    _img_list = []
    path = global_config.cqhttp
    _data = json.loads(data) if isinstance(data,str) else data
    bot = nonebot.get_bot()
    for message in _data["message"]:
        if message["type"] == "image":
            if type == "file":
                _file_detail = await bot.get_image(file=message["data"][type])
                _path = f"{path}/" + str(_file_detail["file"])
                _img_list.append(_path)
            else:
                _img_list.append(message["data"][type])

    return _img_list



def _clear_cache():
    ...

def _tmp_fp()->str:
    return _config['cache'].__str__() + "/" + str(time()).replace(".", "") + ".jpg"

def resize_image(origin: str, max_size: int, k: float) -> Image.Image:
    """接受一个图片, 将其转换为 `jpeg` , 大小不超过 `max_size`,
    过程中产生的临时文件存储于 `_config['cache']` 下

    Args :
        * ``origin :str`` : 源图片目录
        * ``max_size: int`` : 最大大小, 单位为KB
        * ``k: float`` : 每次缩小分辨率的比值

    Returns :
        * ``image: Image.Image`` : 处理后的图片对象
    """
    Image.MAX_IMAGE_PIXELS=None
    _max_size = max_size * 1024  # convert KB to Bytes
    im = Image.open(origin)
    (x, y) = im.size
    if im.format == "gif":
        return im
    _tmp = _tmp_fp()
    im.save(_tmp)

    if getsize(_tmp) <= _max_size:
        return im
    while True:
        _tmp = _tmp_fp()
        (x, y) = (int(x * k), int(y * k))
        _out = im.resize((x, y))
        _out.save(_tmp)
        _out.close()
        if getsize(_tmp) < _max_size:
            return im


async def _upload_custom(
    origin: str, target: str, target_filename: str, max_size: int = 4096
):
    """Upload函数

    Args ::
        `` origin(str): 源文件地址
        `` targer(str): 目标路径
        `` target_filename(str): 目标文件名
        `` max_size(int): 最大文件大小, 大于的直接进行一个压缩 
    """
    if _config["storage"] == "local":
        _origin = resize_image(origin,max_size, 0.9)
        _origin.save(f"{target}/{target_filename}")
        _origin.close()

    else:
        oss2.Bucket.put_object
        ...

def upload_to_local(origin: Union[str,BytesIO], target: str, target_filename: str, max_size: int = 2048) -> Response:
    """上传文件到本地

    Args :
        * `` origin: str`` : 源文件地址
        * `` targer: str`` : 目标路径
        * `` target_filename: str`` : 目标文件名
        * `` max_size: int`` : 最大文件大小, 大于的直接进行一个压缩 
    """
    #try:
    logger.error(type(origin))
    if isinstance(origin, BytesIO):
        _origin = _tmp_fp()
        with open(_origin, "wb") as _f:
            logger.warning(type(origin))
            logger.warning(type(_f))
            _f.write(origin.getbuffer())
    elif isinstance(origin, str):
        _origin = origin
    _origin = resize_image(_origin, max_size, 0.5)
    _format = 'gif' if _origin.format == 'gif' else 'jpeg'
    target = target
    logger.warning(f"target type: {type(target)}")
    logger.warning(f"target_filename type: {type(target_filename)}")

    _target_with_path_format = f'{target}/{target_filename}.{_format}'
    _target_with_path = f'{target}/{target_filename}'
    _target_with_format = f'{target_filename}.{_format}'
    _origin.save(_target_with_path_format,format=_format)
    _origin.close()
    '''
    except Exception as e:
        logger.error(e)
        return Response(ACTION_FAILED, message=f"上传失败, {e}")
    '''
    logger.info(f"上传成功, {_target_with_format}")
    return Response(ACTION_SUCCESS, content=(_target_with_format,_target_with_path_format))


async def _aio_upload_oss():
    ...


async def __make_sign():
    ...


async def _safe_send(id: int, api: str, **message):
    bot = _get_bot(id)
    try:
        await bot.call_api(api, **message)
    except Exception as e:
        logger.error(f"fail to send message, error {e}")


def get_path(path):
    return Path(path).resolve()




def record_id(d:dict,k:Union[dict,str],v:Any):
    if isinstance(k,dict):
        k = k['message_id']
    k=str(k)
    v=str(v)
    d[k] = v

def chat_cooldown_check(chat_cd, cd_id):
    # get current seconds
    now = time.time()
    cd = _config["chat_cooldown"]
    if id in chat_cd and now - chat_cd[id] < cd:
        return True
    return False
