"""
Define some useful functions for AquaBot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import json
from typing import Literal
import nonebot
from nonebot import logger

__version__ = '0.0.1'


def _get_bot(bot_id):
    """
    返回一个bot实例

    Args:
          bot_id(int): bot的qq号

    Returns:
          bot实例一份
    """
    try:
        logger.warning(nonebot.get_bots())
        bot = nonebot.get_bots()[str(bot_id)]
        return bot
    except KeyError:
        logger.error("bot'%s'未连接" % bot_id)


async def get_message_image(data: str, type: Literal['file', 'url'], path: str = '') -> list:
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
    _data = json.loads(data)
    bot = _get_bot(_data['self_id'])
    for msg in _data['message']:
        if msg['type'] == "image":
            if type == "file":
                _file_detail = await bot.get_image(file=msg['data'][type])
                _path = path+'/'+str(_file_detail['file'])
                _img_list.append(_path)
            else:
                _img_list.append(msg['data'][type])

    return _img_list


async def check_image_type(path: str): ...


def get_message_text(data: str) -> str:
    """
    返回消息纯文本
    """
    pass
