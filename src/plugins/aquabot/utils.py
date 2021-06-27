"""
Define some useful functions for AquaBot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""


import json
from typing import Literal
import nonebot
from nonebot import logger
from PIL import Image
from .config import _config
from time import time
from os.path import getsize as _getsize
logger.warning("IMPORT UTILS")
__version__ = '0.0.1'

global_config = nonebot.get_driver().config


def _get_bot(bot_id):
    """
    返回一个bot实例

    Args:
          bot_id(int): bot的qq号

    Returns:
          bot(nonebot.adapters.cqhttp.bot.Bot): bot实例
    """
    try:
        logger.warning(nonebot.get_bots())
        bot = nonebot.get_bots()[str(bot_id)]
        return bot
    except KeyError:
        logger.error("bot'%s'未连接" % bot_id)


async def get_message_image(data: str, type: Literal['file', 'url']) -> list:
    """
    返回一个包含消息中所有图片文件的list, 

    Args: 
          data(str): 消息内容, 来自event.json()
          type('file'): 返回文件名, 需搭配cqhttp客户端的data文件夹获取本地图片(推荐)
          type('url') : 返回图片url, 有概率获取到腾讯禁止爬虫页面导致获取图片失败  
          path(str): 当type为'file'时需指定cqhttp的data文件夹

    Return:
          list: 包含图片绝对路径或url的list
    """
    _img_list = []
    path = global_config.cqhttp
    _data = json.loads(data)
    bot = _get_bot(_data['self_id'])
    for msg in _data['message']:
        if msg['type'] == "image":
            if type == "file":
                _file_detail = await bot.get_image(file=msg['data'][type])
                _path = path + '/' + str(_file_detail['file'])
                # TODO add linux file system
                _img_list.append(_path)
            else:
                _img_list.append(msg['data'][type])

    return _img_list


def get_message_text(data: str) -> str:
    """
    返回消息纯文本
    """
    pass

def _clear_cache(): ...


def _resize_image(file: str, max_size: int, k: float) -> Image.Image:
    """接受一个图片, 将其转换为jpg, 大小不超过max_size,
    过程中产生的临时文件存储于_config['cache']下

    Args:
        file(str): 源图片目录
        max_size(int): 最大大小, 单位为KB
        k(float): 每次缩小分辨率的比值

    Returns:
        image(Image.Image): 处理后的图片对象
    """
    _max_size = max_size * 1024  # convert KB to Bytes
    im = Image.open(file)
    (x, y) = im.size
    if im.format == "gif":
        return im
    else:
        tmp_fp = lambda: _config['cache'] + '/' + str(time.time()).replace('.', '') + '.jpg'
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


async def _upload_custom(origin: str, target: str, target_filename: str, max_size: int = 4096):
    """Upload函数

    Args:
        origin(str): 源文件地址
        targer(str): 目标路径
        target_filename(str): 目标文件名
        max_size(int): 最大文件大小, 大于的直接进行一个压缩 
    """
    if _config['storage'] == "local":
        _origin = _resize_image(origin)

        ...
