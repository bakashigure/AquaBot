import nonebot
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot.log import logger
import pixivpy3 as pixiv
from .config import Config
import httpx
import operator
import oss2

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())


_config = dict()  # 读取配置
_message_hashmap = dict()  # 记录bot发送的message_id与夸图id的键值对


def prehandle():
    _config['storage'] = global_config.AQUA_BOT_PIC_STORAGE
    if _config['storage'] == "local":
        _config['dir'] = global_config.AQUA_BOT_PICTURE_DIR
        # todo 试着写一下文件检查权限(linux)
        # 如果路径不存在就手动创建
        pass
    elif _config['storage'] == "oss":
        _config['id'] = global_config.AQUA_BOT_OSS_ACCESS_KEY_ID
        _config['secret'] = global_config.AQUA_BOT_OSS_ACCESS_KEY_ID_SECRET
        _config['prefix'] = global_config.AQUA_BOT_OSS_PREFIX
        _config['endpoint'] = global_config.AQUA_BOT_OSS_ENDPOINT
        _config['bucket'] = global_config.AQUA_BOT_OSS_BUCKET
        for k, v in _config.items():
            if v == "":
                logger.warning("%s未设置, 请检查.env文件" % k)
                # todo bot咋中断来着, 能直接raise出去吗..

        try:
            oss2.auth(_config['id'], _config['secret'])
        except:
            # todo oss登陆失败
            pass

    else:
        # todo 非正确存储方式处理
        _help_url = ""
        logger.error("存储方式不正确, 请检查.env文件, 有关配置详见%s " % _help_url)
        pass

    _config['refresh_token'] = global_config.AQUA_BOT_PIXIV_REFRESH_TOKEN
    if _config['refresh_token'] == "":
        logger.warning("没有设置pixiv refresh token, pixiv相关功能将不可用")
        # todo

    _config['saucenao_api'] = global_config.AQUA_BOT_SAUCENAO_API
    if _config['saucenao_api'] == "":
        logger.warning("没有设置saucenao api, 搜图相关功能将不可用")
        # todo


aqua = on_command("qua", priority=5)
args = list()


@aqua.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State):
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
    ...


async def upload_aqua(bot: Bot, event: Event): ...
async def delete_aqua(bot: Bot, event: Event): ...
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
        word="湊あくあ", search_target="exact_match_for_tags", sort="date_asc",duration=_duration[args[1]])

    illust_list=[]
    for illust in res_json.illusts:
        __dict={'title':illust.title,'id':illust.id,'bookmark':int(illust.total_bookmarks),'large_url':illust.image_urls['large']}
        illust_list.append(__dict)


    illust_list = sorted(illust_list,key=operator.itemgetter('bookmark'))[::-1]

    _id = args[3]
    async with httpx.AsyncClient() as client:
        headers={'Referer':'https://www.pixiv.net/'}
        r = client.get(illust_list[_id])






async def test_aqua(bot: Bot, event: Event):
    await bot.send(event=event, message="i got test")


async def more_aqua(): ...


@on_command("来点夸图", aliases=("来张夸图", "夸图来"))
async def one_aqua(bot: Bot, event: Event):
    return await random_aqua(bot, event)
