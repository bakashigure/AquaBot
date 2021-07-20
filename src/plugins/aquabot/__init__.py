import json
import operator
from email.utils import formatdate
from json.decoder import JSONDecodeError
from pathlib import Path

import nonebot
import os
from nonebot.adapters.cqhttp.event import MessageEvent
import oss2
import pixivpy3 as pixiv
from aiofiles import open as aiofiles_open
from httpx import AsyncClient
from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import MessageSegment

from .config import Config, _config
from .utils import get_message_image, get_message_text, get_path

__version__ = '0.0.6'
logger.warning("IMPORT INIT")


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())


# logger.info(global_config)

# logger.warning(type(global_config.aqua_bot_pic_storage))
# logger.warning(global_config.aqua_bot_pic_storage)


ACTION_SUCCESS = 200
ACTION_WARNING = 300
ACTION_FAILED = 400

_message_hashmap = dict()  # 记录bot发送的message_id与夸图id的键值对


class Response():
    def __init__(self, code, msg) -> None:
        self.code=code
        self.msg=msg

        if self.code // 100 == 2:
            logger.info(f"{self.code} {self.msg}")
        elif self.code // 100 == 3:
            logger.warning(f"{self.code} {self.msg}")
        elif self.code // 100 == 4:
            logger.error(f"{self.code} {self.msg}")



class DB:
    '''
    {
      "AquaBot": "this file created by aqua bot, please do not modify this file",
      "last_update": "", 
      "version": "",
      "timestamp": "",
      "local": {
            {"pixiv_114514","E://path//pixiv_114514.jpg"},
            {"pixiv_1919810","E://path//pixiv_1919810.jpg"},
            {"114514_4gaw89", "E://path//114514_4gaw89.png"}
      },
      "oss": {} 
    }
    '''

    def __init__(self) -> None:
        self.db = None
        self.type = _config['storage']
        self._lock = False
        self.record_file = _config['database']

        self.cnt=0
        self.used=0

        if self.type == 'oss':
            self.auth = oss2.Auth(_config['access_key_id'], _config['access_key_secret'])
            self.bucket = oss2.Bucket(self.auth, _config['endpoint'], _config['bucket'])

        # 从配置文件中读取夸图数据库, 避免读取本地文件或者oss造成缓慢性能
        # 如果配置文件不存在则生成一个
        try:
            with open(self.record_file, 'r') as f:
                self.db = json.load(f)
                print('DB: %s' % self.db)
        except FileNotFoundError:
            logger.warning("record file not set, will create in %s" % self.record_file)
            init_content = r' { "AquaBot": "this file created by aqua bot, please do not modify this file", "last_update":"", "version":"", "local":{}, "oss":{} }'
            with open(self.record_file, 'w') as f:
                f.write(init_content)
            self.db = json.loads(init_content)
            self.reload()
            logger.warning('DB: %s' % self.db)
            self.save()
        except JSONDecodeError as e:
            logger.error('error reading record file, raw error -> %s' % e)
            exit()

    def reload(self) -> Response:
        '''清空配置, 重新读取本地文件或oss.
        '''
        try:
            self.lock()
            self.db['oss'] = {}
            self.db['local'] = {}
            self.last_update()
            if self.type == 'local':
                for _, _, files in os.walk(_config['dir']):
                    [self.add(f, Path(_config['dir']).joinpath(f).as_posix()) for f in files]
            else:
                # TODO READ OSS FILE LIST
                # OSS2.LISTOBJECTSV2
                ...

            return Response(ACTION_SUCCESS, 'reload success')
        
        except Exception as e:
            return Response(ACTION_FAILED, 'reload failed')

        finally:
            self.unlock()

        ...

    def last_update(self):
        '''更新'last_update'字段
        '''
        self.db['last_update'] = formatdate(usegmt=False)

    def save(self) -> Response:
        '''保存数据库到本地文件
        '''
        if not self.lock:
            self.lock()
            with open(self.record_file, 'w') as f:
                f.write(json.dumps(self.db))
            self.unlock()

            return Response(ACTION_SUCCESS, 'save success')
        else:
            logger.warning('database is now locked.')

    def add(self, k, v):
        self.db[self.type][k] = v

    async def delete(self, k) -> Response:
        _code = ACTION_SUCCESS
        _msg = ''

        try:
            self.lock()
            if self.type == 'oss':
                await self.bucket.delete_object(self.db[self.type][k])
            else:
                try:
                    os.remove(self.db[self.type][k])
                    _msg += 'file "%s" deleted,'%k
                except:
                    _msg += 'failed to delete file "%s",'%k
                    _code = ACTION_FAILED
        finally:
            self.unlock()

        if k in self.db[self.type]:
            del self.db[self.type][k]
            logger.info('deleted record "%s"' % k)
            _msg += 'record "%s" deleted,'%k
        else:
            logger.warning('record "%s" not found' % k)
            _msg += 'record "%s" not found,' %k

        return Response(_code, _msg)

    @classmethod
    def set_type(cls, _type):
        cls.type = _type

    async def get_random(self): ...


    def lock(self):
        self._lock = True

    def unlock(self):
        self._lock = False


DB.set_type(_config['storage'])
db = DB()

aqua = on_command("qua", priority=5)
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
            "help": lambda: help_aqua(bot, event),
            "pixiv": lambda: pixiv_aqua(bot, event),
            "test": lambda: test_aqua(bot, event),
            "reload": lambda: reload_aqua(bot, event)

        }
        return await optdict[option]()

    await switch(args[0], bot, event)


@aqua.got("qua", prompt="114514")
async def bott(bot: Bot, event=Event, state=T_State):
    await aqua.finish("nope")



async def random_aqua(bot: Bot, event: Event):
    """随机发送一张夸图

    Args:
        bot (Bot): bot实例
        event (Event): 事件

    Returns:
    """
    db.get_random() 


async def upload_aqua(bot: Bot, event: Event):
    """上传一张图片
    """
    if _config['storage'] == "local":
        # logger.warning(args)
        # logger.warning(event.json())

        c = await get_message_image(data=event.json(), type='file', path=_config['cqhttp'])
        logger.warning(c)

        pass
    else:
        pass


async def delete_aqua(bot: Bot, event: Event):
    """删除一张夸图
    """
    print(event.json)
    print(event)
    r = await db.delete(args[1])
    await bot.send(event,r.msg)


async def help_aqua(bot: Bot, event: Event): ...
async def search_aqua(bot: Bot, event: Event): ...


async def pixiv_aqua(bot: Bot, event: Event):
    api = pixiv.AppPixivAPI()
    api.set_accept_language('en_us')
    try:
        api.auth(refresh_token=_config['refresh_token'])
    except Exception as e:
        logger.error(e)

    if args[1] not in ['day', 'week', 'month']:
        logger.error("参数错误, 详见/aqua help pixiv")
        # todo

    _duration = {
        "day": "within_last_day",
        "week": "within_last_week",
        "month": "within_last_month"
    }

    res_json = api.search_illust(
        word="湊あくあ", search_target="exact_match_for_tags", sort="date_asc", duration=_duration[args[1]])

    illust_list = []
    for illust in res_json.illusts:
        __dict = {'title': illust.title, 'id': illust.id, 'bookmark': int(
            illust.total_bookmarks), 'large_url': illust.image_urls['large']}
        illust_list.append(__dict)

    illust_list = sorted(
        illust_list, key=operator.itemgetter('bookmark'))[::-1]

    _id = args[3]
    async with AsyncClient() as client:
        headers = {'Referer': 'https://www.pixiv.net/'}
        r = client.get(illust_list[_id])


async def test_aqua(bot: Bot, event: Event):
    await bot.send(event=event, message="i got test")


async def more_aqua(): ...


async def one_aqua(bot: Bot, event: Event):
    return await random_aqua(bot, event)

async def reload_aqua(bot:Bot, event:Event):
    return db.reload()
    MessageSegment.reply()
