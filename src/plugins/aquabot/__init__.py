import json
from email.utils import formatdate
from json.decoder import JSONDecodeError
from os import remove as os_remove
from os import walk as os_walk
from os.path import getsize as os_getsize
from pathlib import Path
import pathlib
from random import randint
from threading import Lock
from re import search as re_search
from copy import deepcopy
from asyncio import sleep as asyncio_sleep

import nonebot
#import oss2
from aiofiles import open as aiofiles_open
from nonebot import get_bot, on_command, require
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, escape, unescape, PokeNotifyEvent
from nonebot.adapters.cqhttp.event import GroupMessageEvent, MessageEvent
from nonebot.adapters.cqhttp.message import Message
from nonebot.log import logger
from nonebot.plugin import on_message, on_notice, on_regex
from nonebot.rule import to_me
from nonebot.typing import T_State
from PIL import Image

from .config import Config, _config
from .pixiv import get_pixiv_image_by_pid, pixiv_search, get_pixiv_image, _safe_get_image
from .response import BaseResponse
from .saucenao import saucenao_search
from .ascii2d import Ascii2D
from .utils import (ACTION_FAILED, ACTION_SUCCESS, ACTION_WARNING,
                    get_message_image, get_message_text, get_path, upload_to_local)
from .utils import record_id as _record_id
from .text import text as _text

logger.warning("importing AquaBot..")

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

# logger.info(global_config)

# logger.warning(type(global_config.aqua_bot_pic_storage))
# logger.warning(global_config.aqua_bot_pic_storage)

scheduler = require("nonebot_plugin_apscheduler").scheduler

p = pathlib.Path("src/plugins/aquabot/database.json").resolve()
logger.warning(p)


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

        self.__version__ = "1.0.0"  # db version

        '''
        if self.type == "oss":
            self.auth = oss2.Auth(
                _config["access_key_id"], _config["access_key_secret"]
            )
            self.bucket = oss2.Bucket(self.auth, _config["endpoint"], _config["bucket"])
        '''
        # 从配置文件中读取夸图数据库, 避免读取本地文件或者oss造成缓慢性能
        # 如果配置文件不存在则生成一个
        try:
            with open(self.record_file, "r") as f:
                self.db = json.load(f)
                logger.info("loaded db")
                #print("DB: %s" % self.db)

        except FileNotFoundError:
            logger.warning("record file not set, will create in %s" % self.record_file)
            init_content = r' { "AquaBot": "this file created by aqua bot, please do not modify this file", "last_update":"", "records":"", "version":"", "total_count":0,"local":{}, "oss":{},"available_count":0,"available":{},"used_count":0,"used":{} }'
            with open(self.record_file, "w") as f:
                f.write(init_content)
            self.db = json.loads(init_content)
            self.reload()
            self.db["version"] = self.__version__
            self.last_update()
            #logger.warning("DB: %s" % self.db)
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
            for _, _, files in os_walk(_config["dir"]):
                [
                    self.add_record(
                        f, Path(_config["dir"]).joinpath(f).as_posix()
                    )
                    for f in files
                ]
        else:
            # TODO READ OSS FILE LIST
            # OSS2.LISTOBJECTSV2
            ...

        self.db["available"] = deepcopy(self.db[self.type])
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

    async def upload(self, *args, **kwargs):
        """添加一个夸图到数据库

        :origin: 夸图原图路径
        """
        if self.type == "local":
            res = upload_to_local(*args, **kwargs)
            if res.status_code // 100 == 2:
                self.add_record(*res.content)
            return res

    def add_record(self, k, v) -> Response:
        if not k in self.db[self.type]:
            self.db['total_count'] += 1
        self.db[self.type][k] = v
        return Response(ACTION_SUCCESS, "add_record record: %s -> %s" % (k, v))

    async def delete(self, k: str) -> Response:

        try:
            k = str(k)
            print(k)
            print(k in self.db[self.type])
            os_remove(self.db[self.type][k])
        except Exception as e:
            return Response(ACTION_FAILED, f"图 片 不 存 在 {e}")

        try:
            del self.db[self.type][k]
        except:
            pass
        try:
            del self.db["available"][k]
        except:
            pass
        try:
            del self.db["used"][k]
        except:
            pass

        return Response(ACTION_SUCCESS, f"已删除{k}")

    @classmethod
    def set_type(cls, _type) -> None:
        cls.type = _type

    def exist(self, k) -> bool:
        return k in self.db[self.type]

    async def get_random(self) -> Response:
        if self.db['available_count'] == 0:
            Response(ACTION_FAILED, "No record available, will refresh records")
            self.refresh()  # 即刻触发refresh
            if self.db["total_count"] == 0:
                return Response(ACTION_FAILED, message="No record available, please upload some pictures :)")
        choice = randint(0, self.db['available_count'] - 1)
        key = self.db_keys[choice]
        del self.db_keys[choice]
        value = self.db["available"][key]

        self.db["used"][key] = value
        self.db["used_count"] += 1

        del self.db["available"][key]
        self.db["available_count"] -= 1

        if _config['storage'] == 'local':
            value = "file:///" + value
        return Response(ACTION_SUCCESS, message="Get a random picture.",content=(key, f"{value}"))

    def get_picture_id(self, k):
        k = str(k)
        return db.messages[k]


DB.set_type(_config["storage"])
db = DB()


aqua = on_command("aqua", priority=5)
args = list()


def record_id(k, v):
    return _record_id(db.messages, k, v)


@aqua.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
    global args
    args = str(event.get_message()).split()
    logger.warning(args)

    async def switch(option, bot, event):
        optdict = {
            "random": lambda: random_aqua(bot, event),
            "more": lambda: more_aqua(bot, event),
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
            "func": lambda: func(bot, event)
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
    Returns:
    """
    res = await db.get_random()
    if res.status_code // 100 == 2:
        key, image = res.content
        id = await bot.send(event, MessageSegment.image(image))
        record_id(id, key)
    else:
        await bot.send(event, MessageSegment.text("并没有能发的图..."))


async def upload_aqua(bot: Bot, event: Event):
    """上传一张图片
    """
    _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }

    # await bot.send(event,str(event.json()))
    if _config["storage"] == "local":
        # logger.warning(args)
        # logger.warning(event.json())

        _response = Response(ACTION_SUCCESS, content='')
        images = await get_message_image(data=event.json(), type="file")
        if len(images) == 0:
            images = args[1:]
            if len(images) == 0:
                return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text("给点图?"))
            for image in images:
                try:
                    int(image)
                except:
                    return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(f"pid必须为纯数字 -> {image}"))
            for pid in images:
                await asyncio_sleep(0.5)
                res, image = (await get_pixiv_image_by_pid(pid, _config['refresh_token'], _REQUESTS_KWARGS, "http://127.0.0.1:7890")).content
                await bot.send(event, MessageSegment.text("\n".join([f"{k}: {v}" for k, v in res.items()])))
                await bot.send(event, MessageSegment.image(image))
                _id = "pixiv_" + res['id'].__str__()
                _id_with_format = _id + '.jpeg'
                if db.exist(_id_with_format) or db.exist(_id):
                    _response.content = "这张图已经被上传了"
                    return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_response.content))
                else:
                    await db.upload(image, _config['dir'], _id)
                    _response.content = f"{_id_with_format} 上传成功"
                    return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_response.content))

        else:
            _user_id = str(event.user_id)[:4]  # 取用户qq前四位用作随机图片名上半段
            logger.warning(images)
            for image in images:
                await asyncio_sleep(0.5)
                res = await saucenao_search(image, _config['saucenao_api'], "http://127.0.0.1:7890")

                if res.status_code // 100 == 2:
                    if res.content['index'] == "pixiv":
                        logger.warning(res.content)
                        _id = "pixiv_" + res.content['data']['illust_id'].__str__()
                        _id_with_format = _id + '.jpeg'
                        _response.content = f"发现pixiv原图, illust_id: {res.content['data']['illust_id'].__str__()}\n"
                        if db.exist(_id_with_format):
                            _response.content += f"{_id_with_format} 已经传过了"
                            return await bot.send(event, MessageSegment.text(_response.content))
                        else:
                            await db.upload(image, _config['dir'], _id)
                            _response.content += f"{_id_with_format} 上传成功"
                            return await bot.send(event, MessageSegment.text(_response.content))
                    else:
                        _id = _user_id + "_" + str(randint(0, 10000000))  # 随便搞点随机数用作用户上传图片名下半段
                        _id_with_format, _ = (await db.upload(image, _config['dir'], _id)).content
                        _response.content += f"{_id_with_format} 上传成功"
                        return await bot.send(event, MessageSegment.text(_response.content))


async def upload_by_reply(bot: Bot, event: Event):
    """通过回复上传图片
    """
    # TODO
    pass


async def delete_aqua(bot: Bot, event: Event):
    """删除一张夸图
    """
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
    await bot.send(event, str(eval(cmd)))


async def func(bot: Bot, event: Event):
    """!debug mode!
    """
    if not _config['debug']:
        return await bot.send(event, MessageSegment.text("debug mode is off."))
    cmd = " ".join(args[1:])
    cmd = unescape(cmd)
    print(cmd)
    _res = await eval(cmd)
    print(type(_res))
    if isinstance(_res, BaseResponse):
        if _res.status_code // 100 == 2:
            await bot.send(event, MessageSegment.text(str(_res.content)))
        else:
            await bot.send(event, MessageSegment.text(_res.message))
    else:
        await bot.send(event, MessageSegment.text(_res))


async def help_aqua(bot: Bot, event: Event):
    return await bot.send(event, MessageSegment.text(_text['chinese']['help']))


async def _pixiv_res_handle(bot: Bot, event: Event, res: BaseResponse):
    if res.status_code // 100 == 2:
        info, image = res.content
        image = MessageSegment.image(image)
        _text = f"{info['title']}\n♡: {info['bookmark']}  pid: {info['id']}"
        _message = MessageSegment.text(_text)
        await bot.send(event, _message)
        await bot.send(event, image)
    else:
        await bot.send(event, MessageSegment.text(res.message))


async def pixiv_aqua(bot: Bot, event: Event):
    logger.warning(args)

    _full = False
    if len(args) == 3:
        _, dur, index = args
        word = "湊あくあ"
    elif len(args) == 4:
        if args[-1] == "full":    # pixiv day 1 full
            word = "湊あくあ"
            _, dur, index, _full = args
            _full = True
        else:   # pixiv some day 1
            _, word, dur, index = args
    elif len(args) == 5:
        _, word, dur, index, full = args
        if (full != "full"):
            return await bot.send(event, MessageSegment.text("参 数 错 误"))
        _full = True
    else:
        return await bot.send(event, MessageSegment.text("参 数 错 误"))

    word = word.replace("_", " ")

    _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
    res = await pixiv_search(refresh_token=_config['refresh_token'], word=word, search_target='partial_match_for_tags', sort='popular_desc', duration=dur, index=index, _REQUESTS_KWARGS=_REQUESTS_KWARGS, proxy="http://127.0.0.1:7890", full=_full)
    await _pixiv_res_handle(bot, event, res)


async def test_aqua(bot: Bot, event: Event):
    await bot.send(event=event, message="i got test")

moremore_aqua = on_command("多来点夸图", priority=6)


@moremore_aqua.handle()
async def _(bot: Bot, event: Event):
    return await more_aqua(bot, event)


async def more_aqua(bot: Bot, event: Event):
    for _ in range(randint(1, 4)):
        key, image = (await db.get_random()).content
        id = await bot.send(event, MessageSegment.image(image))
        record_id(id, key)


one_aqua = on_command("来点夸图", aliases={"夸图来"}, priority=6)


@one_aqua.handle()
async def _(bot: Bot, event: Event):
    return await random_aqua(bot, event)


async def reload_aqua(bot: Bot, event: Event):
    return db.reload()


# 回复搜图
get_id = on_message(priority=7)


@get_id.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    r = re_search(r'\[CQ:reply,id=(-?\d*)]', event.raw_message)
    if r:
        if ((event.self_id == event.reply.sender.user_id) and ("id" in event.get_plaintext())):
            await bot.send(event, MessageSegment.reply(event.user_id) + MessageSegment.text(db.get_picture_id(event.reply.message_id)))
        else:
            if (event.get_plaintext() in ["搜", "aquasearch", "aqua search", "search"]):
                msg = await bot.get_msg(message_id=event.reply.message_id)
                logger.warning(msg)
                logger.warning(type(msg))
                images = await get_message_image(msg, type='file')

                for image in images:
                    await _search_handle(bot, event, image)


poke_aqua = on_notice()  # 戳一戳


@poke_aqua.handle()
async def _(bot: Bot, event: PokeNotifyEvent):
    if event.self_id == event.target_id:
        return await random_aqua(bot, event)
    else:
        pass


async def stats_aqua(bot: Bot, event: Event):
    """统计
    """
    message = MessageSegment.text(f"total: {db.db['total_count']}\navailable: {db.db['available_count']}\n")
    await bot.send(event, message)


async def save_aqua(bot: Bot, event: Event):
    db.save()


async def search_aqua(bot: Bot, event: Event):
    """saucenao search module
    """
    images = await get_message_image(data=event.json(), type="file")
    if len(images) == 0:
        await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text("给点图?"))
    for image in images:
        await _search_handle(bot, event, image)


async def _search_handle(bot, event, image):
    res = await saucenao_search(image, _config['saucenao_api'], "http://127.0.0.1:7890")
    logger.warning(res.status_code)
    logger.warning(res.content)
    if res.status_code // 100 == 2:
        _s = f"index: {res.content['index']}\nrate: {res.content['rate']}\n" + '\n'.join([f"{k}: {v}"for k, v in res.content['data'].items()])

        await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s))
    else:
        a = Ascii2D()
        res = await a.search(image)

        if res.status_code // 100 == 2:
            _s = "\n".join([f"{k}: {v}"for k, v in res.content.items()])
            return await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text(_s))
        elif res.status_code // 100 == 3:
            _s1 = "请自行对比缩略图(\n" + "\n".join([f"{k}: {v}"for k, v in res.content[0].items()])
            _s2 = "请自行对比缩略图(\n" + "\n".join([f"{k}: {v}"for k, v in res.content[2].items()])
            image1 = (await _safe_get_image(res.content[1], proxies="http://127.0.0.1:7890")).content
            image2 = (await _safe_get_image(res.content[3], proxies="http://127.0.0.1:7890")).content
            await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s1) + MessageSegment.image(image1))
            await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s2) + MessageSegment.image(image2))

        # await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(res.message))

# 每日一夸


@scheduler.scheduled_job('cron', hour=17, minute=46, second=10)
async def daily_aqua():
    _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
    bot = get_bot()
    info, image = (await pixiv_search(refresh_token=_config['refresh_token'], word="湊あくあ", search_target='partial_match_for_tags', sort='popular_desc', duration="day", index=1, _REQUESTS_KWARGS=_REQUESTS_KWARGS, proxy="http://127.0.0.1:7890", full=True)).content
    _text = MessageSegment.text(f"#每日一夸#\n{info['title']}\n♡: {info['bookmark']}  pid: {info['id']}")
    for group in _config['daily']:
        await asyncio_sleep(1)
        print(type(image))
        print(image)
        await bot.call_api("send_group_msg", **{"group_id": group, "message": _text})
        await bot.call_api("send_group_msg", **{"group_id": group, "message": MessageSegment.image(image)})
