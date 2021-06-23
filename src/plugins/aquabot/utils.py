"""
Define some useful functions for AquaBot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import json
from typing import Optiolal, Literal

__version__ = '0.0.1'


def get_message_image(data: str, type: Literal['file', 'url']) -> list:
    """
    返回一个包含消息中所有图片文件的list, 

    Args: data(str): 消息内容, 来自event.json()
          type('file'): 返回文件名, 需搭配cqhttp客户端的data文件夹获取本地图片(推荐)
          type('url') : 返回图片url, 有概率获取到腾讯禁止爬虫页面导致获取图片失败  
    """
    _img_list = []
    _data = json.load(data)
    for msg in _data['message']:
        if msg['type'] == "image":
            _img_list.append(msg['data'[type]])

    return _img_list


def get_message_text(data: str) -> str:
    """
    返回消息纯文本
    """
