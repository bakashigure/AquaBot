import json
from email.utils import formatdate
from json.decoder import JSONDecodeError
from pathlib import Path
from random import randint
from threading import Lock
from PIL import Image

import nonebot
import os
from nonebot.adapters.cqhttp.event import MessageEvent
import oss2
from aiofiles import open as aiofiles_open
from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import MessageSegment, escape, unescape

from .pixiv import pixiv_search

from .config import Config, _config
from .saucenao import saucenao_search
from .utils import (
    get_message_image,
    get_message_text,
    get_path,
    ACTION_FAILED,
    ACTION_SUCCESS,
    ACTION_WARNING,
)

from .response import BaseResponse

__version__ = "0.0.6"
logger.warning("IMPORT AQUABOT")

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

# logger.info(global_config)

# logger.warning(type(global_config.aqua_bot_pic_storage))
# logger.warning(global_config.aqua_bot_pic_storage)
class Response(BaseResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if status := self.status_code // 100 == 2:
            logger.info(self.log)
        elif status == 3:
            logger.warning(self.log)
        else:
            logger.error(self.log)


class DB:
    """
    {
      "AquaBot": "this file created by aqua bot, please do not modify this file",
      "last_update": "", 
      "records": "",
      "version":"",
      "local": {
            {"pixiv_114514","E://path//pixiv_114514.jpg"},
            {"pixiv_1919810","E://path//pixiv_1919810.jpg"},
            {"114514_4gaw89", "E://path//114514_4gaw89.png"}
      },
      "oss": {} ,
      "used": {}
    }
    """

    def __init__(self) -> None:
        self.db = None  # 本体
        self.db_keys: list = []
        self.type = _config["storage"]  # 存储类型, 'oss' or 'local'
        self.record_file = _config["database"]  # 记录文件路径
        self.messages = dict()  # 记录bot发送的message_id与夸图id的键值对

        self.__version__ = "1.0.0"

        if self.type == "oss":
            self.auth = oss2.Auth(
                _config["access_key_id"], _config["access_key_secret"]
            )
            self.bucket = oss2.Bucket(self.auth, _config["endpoint"], _config["bucket"])

        # 从配置文件中读取夸图数据库, 避免读取本地文件或者oss造成缓慢性能
        # 如果配置文件不存在则生成一个
        try:
            with open(self.record_file, "r") as f:
                self.db = json.load(f)
                print("DB: %s" % self.db)

        except FileNotFoundError:
            logger.warning("record file not set, will create in %s" % self.record_file)
            init_content = r' { "AquaBot": "this file created by aqua bot, please do not modify this file", "last_update":"", "records":"", "version":"", "total_count":0,"local":{}, "oss":{},"available_count":0,"available":{},"used_count":0,"used":{} }'
            with open(self.record_file, "w") as f:
                f.write(init_content)
            self.db = json.loads(init_content)
            self.reload()
            self.db["version"] = self.__version__
            self.last_update()
            logger.warning("DB: %s" % self.db)
            self.save()

        except JSONDecodeError as e:
            logger.error("JSON decode error -> %s" % e)
            exit()

        self.refresh()

    def refresh(self) -> Response:
        """把发过的图片重新添加到图库
        """
        self.db["available"].update(self.db["used"])
        self.db["used"] = {}
        self.db_keys = list(self.db[self.type].keys())
        self.db["total_count"] = len(self.db_keys)
        self.db["available_count"] = self.db["total_count"]
        self.db["used_count"] = 0
        self.last_update()
        return Response(ACTION_SUCCESS, "refresh success, db_total:%s" % self.db["total_count"])

    def reload(self) -> Response:
        """清空配置, 重新读取本地文件或oss.
        """
        
        self.db["oss"] = {}
        self.db["local"] = {}
        self.db["used"] = {}

        if self.type == "local":
            for _, _, files in os.walk(_config["dir"]):
                [
                    self.add(
                        f, Path(_config["dir"]).joinpath(f).as_posix()
                    )
                    for f in files
                ]
        else:
            # TODO READ OSS FILE LIST
            # OSS2.LISTOBJECTSV2
            ...

        self.db["available"] = self.db[self.type]
        self.refresh()
        return Response(ACTION_SUCCESS, "reload success")


    def last_update(self) -> Response:
        """更新'last_update'字段
        """
        self.db["last_update"] = formatdate(usegmt=False)
        return Response(ACTION_SUCCESS, "last_update: %s" % self.db["last_update"])

    def save(self) -> Response:
        """保存数据库到本地文件
        """

        with open(self.record_file, "w") as f:
            f.write(json.dumps(self.db))

        return Response(ACTION_SUCCESS, "save success")

    def add(self, k, v) -> Response:
        if not k in self.db[self.type]:
            self.db['total_count'] += 1
        self.db[self.type][k] = v
        return Response(ACTION_SUCCESS, "add record: %s -> %s" % (k, v))

    async def delete(self, k: str) -> Response:
        _code = ACTION_SUCCESS
        _message = ""

        if self.type == "oss":
            await self.bucket.delete_object(self.db[self.type][k])
        else:
            try:
                os.remove(self.db[self.type][k])
                _message += 'file "%s" deleted,' % k
            except:
                _message += 'failed to delete file "%s",' % k
                _code = ACTION_FAILED

        if k in self.db[self.type]:
            del self.db[self.type][k]
            logger.info('delete record "%s"' % k)
            _message += 'record "%s" deleted,' % k
        else:
            logger.warning('record "%s" not found' % k)
            _message += 'record "%s" not found,' % k

        return Response(_code, _message)

    @classmethod
    def set_type(cls, _type) -> None:
        cls.type = _type

    async def get_random(self) -> Response:
        if self.db['available_count'] == 0:
            Response(ACTION_FAILED, "no record available, will refresh records")
            self.refresh()  # 即刻触发refresh
            if self.db["total_count"] == 0:
                return Response(ACTION_FAILED, "no record available")
        choice = randint(0, self.db['available_count'] - 1)
        key = self.db_keys[choice]
        del self.db_keys[choice]
        value = self.db["available"][key]

        self.db["used"][key] = value
        self.db["used_count"] += 1

        del self.db["available"][key]
        self.db["available_count"] -= 1

        if _config['storage']=='local':
            value="file:///" + value
        return Response(ACTION_SUCCESS, "%s" % value)



DB.set_type(_config["storage"])
db = DB()

aqua = on_command("aqua", priority=5)
args = list()


async def misc():
    """定时脚本
    清理cache, 保存json.
    """
    ...


@aqua.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    global args
    args = str(event.get_message()).split()
    logger.warning(args)

    async def switch(option, bot, event):
        optdict = {
            "random": lambda: random_aqua(bot, event),
            "upload": lambda: upload_aqua(bot, event),
            "delete": lambda: delete_aqua(bot, event),
            "search": lambda: search_aqua(bot, event),
            "help": lambda: help_aqua(bot, event),
            "pixiv": lambda: pixiv_aqua(bot, event),
            "test": lambda: test_aqua(bot, event),
            "reload": lambda: reload_aqua(bot, event),
            "debug": lambda: debug(bot, event),
            "stats": lambda: stats_aqua(bot, event),
            "save": lambda: save_aqua(bot, event),
            "func":lambda:func(bot,event)
        }
        return await optdict[option]()

    await switch(args[0], bot, event)


"""
@aqua.got("qua", prompt="114514")
async def bott(bot: Bot, event=Event, state=T_State):
    await aqua.finish("nope")
"""


async def random_aqua(bot: Bot, event: Event):
    """随机发送一张夸图

    Args :
        >>> bot (Bot): bot实例
        >>> event (Event): 事件

    Returns:
    """
    res = await db.get_random()
    if res.code // 100 == 2:
        _message = MessageSegment.image(res.message)
        await bot.send(event, _message)
    else:
        await bot.send(event, MessageSegment.text("no available images!"))


async def upload_aqua(bot: Bot, event: Event):
    """上传一张图片
    """
    if _config["storage"] == "local":
        # logger.warning(args)
        # logger.warning(event.json())

        images = await get_message_image(data=event.json(), type="file",)
        logger.warning(images)
        for image in images:
            res = await saucenao_search(image)
            if res.status_code // 100 == 2 and res.content['index']=="pixiv":
                _id = "pixiv_"+res.content['illust_id']
            else:
                pass
        pass
    else:
        pass

async def upload_by_reply(bot: Bot, event: Event):
    """上传图片
    """
    if _config["storage"] == "local":
        # logger.warning(args)
        # logger.warning(event.json())

        c = await get_message_image(data=event.json(), type="file")
        logger.warning(c)

        pass
    else:
        pass

async def upload_by_pid(pid):
    ...

async def upload_by_image(path:str,user_id):
    ...

async def delete_aqua(bot: Bot, event: Event):
    """删除一张夸图
    """
    print(event.json)
    print(event)
    res = await db.delete(args[1])
    answer = MessageSegment.reply(event.message_id) + MessageSegment.text(res.message)
    await bot.send(event, answer)


async def debug(bot: Bot, event: Event):
    """!debug mode!
    """
    if not _config['debug']:
        return await bot.send(event, MessageSegment.text("debug mode is off."))
    cmd = " ".join(args[1:])
    cmd = unescape(cmd)
    print(cmd)
    await bot.send(event,str(eval(cmd)))

async def func(bot:Bot,event:Event):
    """!debug mode!
    """
    if not _config['debug']:
        return await bot.send(event, MessageSegment.text("debug mode is off."))
    cmd = " ".join(args[1:])
    cmd = unescape(cmd)
    print(cmd)
    print(await eval(cmd))


async def help_aqua(bot: Bot, event: Event):
    ...




async def pixiv_aqua(bot: Bot, event: Event):
    
    _, dur, index = args


    _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
    res = await pixiv_search(refresh_token=_config['refresh_token'],word='湊あくあ',search_target='exact_match_for_tags',sort='popular_desc',duration=dur,index=index,_REQUESTS_KWARGS=_REQUESTS_KWARGS,proxy="http://127.0.0.1:7890")
    if res.status_code // 100 == 2:
        info,image=res.content
        image=Image.open(image)
        _text = f"title: {info['title']}\nillust_id: {info['id']}\n♡: {info['bookmark']}"
        _message = MessageSegment.text(_text)
        #+MessageSegment.image(image)
        await bot.send(event,_message)
        await bot.send(event,image)
    else:
        await bot.send(event,MessageSegment.text(res.message))



async def test_aqua(bot: Bot, event: Event):
    await bot.send(event=event, message="i got test")


async def more_aqua():
    ...


async def one_aqua(bot: Bot, event: Event):
    return await random_aqua(bot, event)


async def reload_aqua(bot: Bot, event: Event):
    return db.reload()
    MessageSegment.reply()




async def stats_aqua(bot: Bot, event: Event):
    """统计
    """
    message = MessageSegment.text(f"total: {db.db['total_count']}\navailable: {db.db['available_count']}\n")
    await bot.send(event, message)


async def save_aqua(bot: Bot, event: Event):
    db.save()

async def search_aqua(bot:Bot,event:Event):
    """saucenao search module
    """
    images = await get_message_image(data=event.json(), type="file")
    for image in images:
        res =await saucenao_search(file_path=image,APIKEY=_config['saucenao_api'],proxies="http://127.0.0.1:7890")
        if res.status_code // 100 == 2:
            _s = f"index: {res.content['index']}\nrate: {res.content['rate']}\n" + '\n'.join([f"{k}: {v}"for k, v in res.content['data'][res.content['index']].items()])

            await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text(res.content))
        else:
            await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text(res.message))
        

