from json.decoder import JSONDecodeError
import operator
from email.utils import formatdate

import oss2
import pixivpy3 as pixiv
from aiofiles import open as aiofiles_open
from httpx import AsyncClient
from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp.utils import escape, unescape
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State

from .config import Config, _config, prehandle
from .utils import *
__version__= '0.0.5'
logger.warning("IMPORT INIT")


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())


# logger.info(global_config)

# logger.warning(type(global_config.aqua_bot_pic_storage))
# logger.warning(global_config.aqua_bot_pic_storage)


_message_hashmap = dict()  # 记录bot发送的message_id与夸图id的键值对


class DB:
    '''
    { 
      "last_update": "", 
      "version": "",
      "local": {
            "pixiv_114514":"E://PATH//pixiv_114514.jpg",
            "pixiv_1919810":"E://PATH//pixiv_1919810.jpg",
            "114514_4gaw89":"E://PATH//114514_4gaw89.png",
      },
      "oss": {} }
    '''
    def __init__(self, record_file) -> None:
        self.db = None
        self.type = _config['storage']
        try:
            with open(record_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            logger.warning("record file not set, will create in %s" %record_file)
            _init_content = r' {"last_update":"", "version":"", "local":{}, "oss":{} }'
            with open(record_file, 'w') as f:
                f.write(_init_content)
            self.db = json.loads(_init_content)
        except JSONDecodeError as e:
            logger.error('error reading record file, raw error -> %s'%e)
            exit()

    async def _update(self):...
    async def add(self): ...
    async def delete(self): ...
    async def get_random(self):...
    async def delete(self):...


aqua = on_command("qua", priority=5)
args = list()


def _on_start(record_file=_config['database']):
    """每次启动时初始化图库, 并且动态维护图库.
    数据量不大, 就不使用SQL了.
    """
    if not record_file:
        logger.warning("record file not set")
    # open file
        # 先判断文件是否存在, 如果存在, 则直接读取
    # 如果不存在, 则创建并初始化
    # 初始化图库
    # 格式:
    # {
    #     "id1": {
    #         "title": "",
    #         "pic": "",
    #         "tags": [],
    #         "bookmarks": 0
    #     },
    #     "id2": {
    #         "title": "",
    #         "pic": "",
    #         "tags": [],
    #         "bookmarks": 0
    #     }
    # }
    # 判断文件是否存在, 存在则直接读取
    # 如果不存在, 则创建并初始化
    try:
        with open(record_file, 'r') as f:
            db = json.load(f)
    except FileNotFoundError:
        _init_content = r' {"local":{},"oss":{} }'

        with open(record_file, 'w') as f:
            f.write(_init_content)
    # 初始化
    _message_hashmap = {
        "id1": {
            "title": "",
            "pic": "",
            "tags": [],
            "bookmarks": 0
        },
        "id2": {
            "title": "",
            "pic": "",
            "tags": [],
            "bookmarks": 0
        }
    }
    logger.warning("初始化图库")
    return _message_hashmap


_on_start('')


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

        }
        return await optdict[option]()

    await switch(args[0], bot, event)


@aqua.got("qua", prompt="114514")
async def bott(bot: Bot, event=Event, state=T_State):
    await aqua.finish("nope")


async def _get_aqua_pic(): ...


async def random_aqua(bot: Bot, event: Event):
    """随机发送一张夸图

    Args:
        bot (Bot): bot实例
        event (Event): 事件

    Returns:
    """
    if _config['storage'] == 'local':
        ...
    else:
        ...


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
