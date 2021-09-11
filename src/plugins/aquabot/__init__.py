import json
from email.utils import formatdate
from json.decoder import JSONDecodeError
from os import remove as os_remove
from os import walk as os_walk
from os.path import getsize as os_getsize
from pathlib import Path
from random import randint
from threading import Lock
from re import search as re_search

import nonebot
#import oss2
from aiofiles import open as aiofiles_open
from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import MessageSegment, escape, unescape,PokeNotifyEvent
from nonebot.adapters.cqhttp.event import GroupMessageEvent, MessageEvent
from nonebot.log import logger
from nonebot.plugin import on_message, on_notice, on_regex
from nonebot.rule import to_me
from nonebot.typing import T_State
from PIL import Image

from .config import Config, _config
from .pixiv import pixiv_search
from .response import BaseResponse
from .saucenao import saucenao_search
from .utils import (ACTION_FAILED, ACTION_SUCCESS, ACTION_WARNING,
                    get_message_image, get_message_text, get_path,upload_to_local)
from .utils import record_id as _record_id
from .text import text as _text

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

    async def upload(self,*args,**kwargs):
        """添加一个夸图到数据库

        :origin: 夸图原图路径
        """
        if self.type == "local":
            res =  upload_to_local(*args,**kwargs)
            if res.status_code//100 == 2:
                self.add_record(*res.content)
            return res

    def add_record(self, k, v) -> Response:
        if not k in self.db[self.type]:
            self.db['total_count'] += 1
        self.db[self.type][k] = v
        return Response(ACTION_SUCCESS, "add_record record: %s -> %s" % (k, v))

    async def delete(self, k: str) -> Response:

        try:
            k=str(k)
            os_remove(self.db[self.type][k])
        except Exception as e:
            return Response(ACTION_FAILED,f"图 片 不 存 在" )

        try:
            del self.db[self.type][k]
        except:pass
        try:
            del self.db["available"][k]
        except:pass
        try:
            del self.db["used"][k]
        except:pass 

        return Response(ACTION_SUCCESS,f"已删除{k}")

    

    @classmethod
    def set_type(cls, _type) -> None:
        cls.type = _type

    def exist(self,k)->bool:
        return k in self.db[self.type]

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
        return Response(ACTION_SUCCESS, content=(key,f"{value}"))

    def get_picture_id(self,k):
        k= str(k)
        return db.messages[k]


DB.set_type(_config["storage"])
db = DB()



aqua = on_command("aqua", priority=5)
args = list()

def record_id(k,v):
    return _record_id(db.messages, k, v)
    

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
            "more": lambda: more_aqua(bot,event),
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
    Returns:
    """
    res = await db.get_random()
    if res.status_code // 100 == 2:
        key,image = res.content
        id = await bot.send(event, MessageSegment.image(image))
        record_id(id,key)
    else:
        await bot.send(event, MessageSegment.text("no available images!"))


async def upload_aqua(bot: Bot, event: Event):
    """上传一张图片
    """
    #await bot.send(event,str(event.json()))
    if _config["storage"] == "local":
        # logger.warning(args)
        # logger.warning(event.json())

        _response = Response(ACTION_SUCCESS,content='')
        images = await get_message_image(data=event.json(), type="file")
        if len(images)==0:
            return await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text("给点图?"))
        _user_id = str(event.user_id)[:4]
        logger.warning(images)
        for image in images:
            res = await saucenao_search(image,_config['saucenao_api'],"http://127.0.0.1:7890")

            if res.status_code // 100 == 2:
                if res.content['index']=="pixiv":
                    logger.warning(res.content)
                    _id = "pixiv_"+res.content['data']['pixiv']['illust_id'].__str__()
                    _id_with_format = _id+'.jpeg'
                    _response.content=f"发现pixiv原图, illust_id: {res.content['data']['pixiv']['illust_id'].__str__()}\n"
                    if db.exist(_id_with_format):
                        _response.content += f"{_id_with_format} 已经传过了."
                        return await bot.send(event, MessageSegment.text(_response.content))
                    else:
                        await db.upload(image,_config['dir'],_id)
                        _response.content += f"{_id_with_format} 上传成功."
                        return await bot.send(event, MessageSegment.text(_response.content))
            else:
                _id = _user_id+"_"+str(randint(0,10000000))
                _id_with_format,_ = (await db.upload(image,_config['dir'],_id)).content
                _response.content += f"{_id_with_format} uploaded."
                return await bot.send(event, MessageSegment.text(_response.content))
            
    else:
        pass

async def upload_by_reply(bot: Bot, event: Event):
    """通过回复上传图片
    """
    # TODO 
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
    _res = await eval(cmd)
    print(type(_res))
    if isinstance(_res,BaseResponse):
        if _res.status_code//100==2:
            await bot.send(event,MessageSegment.text(str(_res.content)))
        else:
            await bot.send(event,MessageSegment.text(_res.message))
    else:
        await bot.send(event,MessageSegment.text(_res))


async def help_aqua(bot: Bot, event: Event):
    return await bot.send(event,MessageSegment.text(_text['chinese']['help']))


async def pixiv_aqua(bot: Bot, event: Event):
    logger.warning(args)
    logger.warning(len(args))
    if len(args)==3:
        _,dur,index =args
        word="湊あくあ"
    elif len(args)==4:
        _,word,dur,index = args
    else:
        return await bot.send(event, MessageSegment.text("参 数 错 误"))

    _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
    res = await pixiv_search(refresh_token=_config['refresh_token'],word=word,search_target='partial_match_for_tags',sort='popular_desc',duration=dur,index=index,_REQUESTS_KWARGS=_REQUESTS_KWARGS,proxy="http://127.0.0.1:7890")
    if res.status_code // 100 == 2:
        info,image=res.content
        image=MessageSegment.image(image)
        _text = f"title: {info['title']}\n♡: {info['bookmark']}\npid: {info['id']}"
        _message = MessageSegment.text(_text)
        await bot.send(event,_message)
        await bot.send(event,image)
    else:
        await bot.send(event,MessageSegment.text(res.message))



async def test_aqua(bot: Bot, event: Event):
    await bot.send(event=event, message="i got test")

moremore_aqua = on_command("多来点夸图",priority=6)
@moremore_aqua.handle()
async def _(bot:Bot,event:Event):
    return await more_aqua(bot,event)

async def more_aqua(bot:Bot,event:Event):
    for _ in range(randint(1,4)):
        key,image=(await db.get_random()).content
        id = await bot.send(event,MessageSegment.image(image))
        record_id(id,key)

one_aqua = on_command("来点夸图",aliases={"夸图来"},priority=6)
@one_aqua.handle()
async def _(bot: Bot, event: Event):
    return await random_aqua(bot, event)


async def reload_aqua(bot: Bot, event: Event):
    return db.reload()
    MessageSegment.reply()

get_id = on_message(priority=7)
@get_id.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    r = re_search(r'\[CQ:reply,id=(-?\d*)]', event.raw_message)
    if r:
        if event.self_id == event.reply.sender.user_id:
            await bot.send(event,MessageSegment.reply(event.user_id)+MessageSegment.text(db.get_picture_id(event.reply.message_id)))




poke_aqua=on_notice()
@poke_aqua.handle()
async def _(bot:Bot,event:PokeNotifyEvent):
    if event.self_id == event.target_id:
        return await random_aqua(bot,event)
    else:pass



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
    if len(images) == 0:
        await bot.send(event, MessageSegment.reply(event.message_id)+MessageSegment.text("给点图?"))
    for image in images:
        res =await saucenao_search(file_path=image,APIKEY=_config['saucenao_api'],proxies="http://127.0.0.1:7890")
        if res.status_code // 100 == 2:
            _s = f"index: {res.content['index']}\nrate: {res.content['rate']}\n" + '\n'.join([f"{k}: {v}"for k, v in res.content['data'][res.content['index']].items()])

            await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text(_s))
        else:
            await bot.send(event,MessageSegment.reply(event.message_id)+MessageSegment.text(res.message))
        

