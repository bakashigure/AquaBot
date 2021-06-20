import nonebot
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot.log import logger
import pixivpy3 as pixiv
from .config import Config,prehandle
import httpx
import operator
import oss2


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

prehandle()

#logger.info(global_config)

#logger.warning(type(global_config.aqua_bot_pic_storage))
#logger.warning(global_config.aqua_bot_pic_storage)



_message_hashmap = dict()  # 记录bot发送的message_id与夸图id的键值对



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



async def one_aqua(bot: Bot, event: Event):
    return await random_aqua(bot, event)
