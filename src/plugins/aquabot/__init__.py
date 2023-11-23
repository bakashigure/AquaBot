# @Author: bakashigure
# @Date: 2022-01-31 17:28:45
# @Last Modified by:   bakashigure
# @Last Modified time: 2022-01-31 17:28:45

from ast import alias
import pathlib
import time
from asyncio import log, sleep as asyncio_sleep
from random import randint, random
from re import M, search as re_search
import time

from nonebot import get_bot, get_driver, on_command, require
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Message as v11Message
from nonebot.adapters.onebot.v11 import MessageSegment, PokeNotifyEvent, escape, unescape
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, GroupMessageEvent, MessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg
from nonebot.plugin import on_message, on_notice, on_regex
from nonebot.rule import to_me
from PIL import Image
from setuptools import Command
from soupsieve import match
from collections import defaultdict

from .ascii2d import Ascii2D
from .config import Config, _config
from .db import DB
from .pixiv import _safe_get_image, get_pixiv_image, get_pixiv_image_by_pid, pixiv_search, get_pixiv_image_by_id
from .response import BaseResponse
from .saucenao import saucenao_search
from .text import text as _text
from .utils import ACTION_FAILED, ACTION_SUCCESS, ACTION_WARNING, get_message_image, get_path
from .utils import record_id as _record_id
from .utils import upload_to_local
from .chatgpt import ChatBot
from .cat import cat_detect

logger.warning("importing AquaBot..")

global_config = get_driver().config
plugin_config = Config(**global_config.dict())

# logger.info(global_config)

# logger.warning(type(global_config.aqua_bot_pic_storage))
# logger.warning(global_config.aqua_bot_pic_storage)


ChatBot = ChatBot(api_key=_config["openai_api_key"],
                  max_token=_config["openai_max_token"],
                  enable_cd = True,
                  proxy_url = "http://127.0.0.1:7890",
                  cd = _config["openai_cd"],
                  block_list = _config["openai_block_list"],
                  context_support = True,
                  pro_users = _config["openai_pro_users"],
                  )

logger.add("aqua.log", rotation="00:00") # split by day

scheduler = require("nonebot_plugin_apscheduler").scheduler

class Response(BaseResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if status := self.status_code // 100 == 2:
            logger.info(self.log)
        elif status == 3:
            logger.warning(self.log)
        else:
            logger.error(self.log)


DB.set_type(_config["storage"])
db = DB()


def record_id(k, v):
    return _record_id(db.messages, k, v)


randomMatcher = on_command("aqua random", block=True, aliases={"来点夸图", "夸图来"}, priority=7)
moreMatcher = on_command("aqua more", block=True, aliases={"多来点夸图", "来多点夸图"}, priority=7)
searchMatcher = on_command("aqua search", block=True, priority=7)
pixivMatcher = on_command("aqua pixiv", block=True, priority=7)
uploadMatcher = on_command("aqua upload", block=True, priority=7)
helpMatcher = on_command("aqua help", block=True, priority=7)
deleteMatcher = on_command("aqua delete", block=True, priority=7)
statsMatcher = on_command("aqua stats", block=True, priority=7)
saveMatcher = on_command("aqua save", block=True, priority=7)
reloadMatcher = on_command("aqua reload", block=True, priority=7)
getIllustMatcher = on_command("aqua illust", block=True, priority=7)
chatMatcher = on_command("aqua chat", block=True, priority=7, aliases={"ac"})
resetChatMatcher = on_command("aqua resetchat", block=True, priority=7)
catMatcher = on_message(priority=8, block=False)

replySearchMatcher = on_message(priority=8, block=True)
pokeMatcher = on_notice()  # 戳一戳


debugMatcher = on_command("aqua debug")


"""
@aqua.handle()
async def handle_first_receive(bot: Bot, event: Event):
    global args
    args = str(event.get_message()).split()
    if "aqua" in args[0]:
        del args[0]
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
            "func": lambda: func(bot, event),
        }
        return await optdict[option]()

    await switch(args[0], bot, event)

"""


async def get_illust_aqua(bot: Bot, event: Event, args: list):
    """点图

    Args:
        bot (Bot): bot
        event (Event): event
        id (str): pid
    """
    logger.warning(args)
    if not args:
        return await bot.send(event, "参 数 错 误")
    if len(args) == 1:  # pid
        pid = args[0]
        size = "large"
        if not pid.isdigit():
            return await bot.send(event, "pid必须为纯数字")
    elif len(args) == 2:  # day 1 full | word day 1
        pid = args[0]
        if not pid.isdigit():
            return await bot.send(event, "pid必须为纯数字")
        size = args[1]
        if size not in ["medium", "large", "original"]:
            return await bot.send(event, "请选择['medium','large','original']中的一项")
    else:
        return await bot.send(event, "参 数 错 误")

    logger.warning(f"pid: {pid} size: {size}")
    resp = await get_pixiv_image_by_id(pid)
    if resp.status_code == ACTION_FAILED:
        await getIllustMatcher.finish("获取上游api失败")

    d = resp.content
    images = []
    if "error" in d:
        return await bot.send(event,"请求资源失败, "+d["error"]["user_message"])
    if d["illust"]["meta_single_page"]: # 判断单图还是图集
        if size == 'original':
            images.append(d["illust"]["meta_single_page"]["original_image_url"])
        else:
            images.append(d["illust"]["image_urls"][size])
    else: # 图集
        images.extend(image["image_urls"][size] for image in d["illust"]["meta_pages"])
    if not images:
        return await bot.send(event, "请求资源失败")

    for image in images:
        ret = await get_pixiv_image(image,"http://127.0.0.1:7890")
        if (ret.status_code == ACTION_SUCCESS):
            await bot.send(event, MessageSegment.image(ret.content))


@getIllustMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    args_list = args.extract_plain_text().split()
    logger.warning("enter handle")
    logger.warning(args_list)
    if args_list:
        matcher.set_arg("args_list", args_list)  # type: ignore

@getIllustMatcher.got("args_list", prompt="参数来!")
async def _(event: MessageEvent, args: list = Arg("args_list")):
    logger.warning("enter got")
    logger.warning(args)
    if isinstance(args, Message):
        args = event.message.extract_plain_text().split()
    if not args:
        await getIllustMatcher.reject("参数来!")
    await get_illust_aqua(get_bot(), event, args)


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


@randomMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    plain_text = args.extract_plain_text()  # random图片数
    if plain_text.isdigit():
        matcher.set_arg("images", args)
    else:
        matcher.set_arg("images", v11Message("1"))


@randomMatcher.got("images")
async def _(event: MessageEvent, images: str = ArgPlainText("images")):
    if images and images.isdigit():
        if int(images) < 1:  # isdigit 居然不能判负数
            await randomMatcher.finish(MessageSegment.text("请输入 [1, 5] 之间的数字"))
        if int(images) > 5:
            await randomMatcher.finish(MessageSegment.text("一次最多五张夸图哦"))
        for __ in range(int(images)):
            await random_aqua(get_bot(), event)
            await asyncio_sleep(0.5)
    else:
        await random_aqua(get_bot(), event)


async def upload_aqua(bot: Bot, event: MessageEvent, image: str):
    """上传一张图片
    """

    async def _up_user():  # 传未找到来源的图
        _id = f"{_user_id}_{str(randint(0, 10000000))}"
        _id_with_format, _ = (await db.upload(image, _config["dir"], _id)).content
        _response.content += f"{_id_with_format} 上传成功"
        return await bot.send(event, MessageSegment.text(_response.content))

    async def _up_exist():  # 存在id的图
        if db.exist(_id_with_format) or db.exist(_id):
            _response.content = "这张图已经被上传了"
        else:
            await db.upload(image, _config["dir"], _id)
            _response.content = f"{_id_with_format} 上传成功"

        return await bot.send(
            event, MessageSegment.reply(event.message_id) + MessageSegment.text(_response.content)
        )

    _REQUESTS_KWARGS = {
        "proxies": {"https": "http://127.0.0.1:7890",},
    }

    if _config["storage"] == "local":
        _response = Response(ACTION_SUCCESS, content="")

        if image.isdigit():
            res, image = (
                await get_pixiv_image_by_pid(image, _config["refresh_token"], _REQUESTS_KWARGS, "http://127.0.0.1:7890")
            ).content
            await bot.send(event, MessageSegment.text("\n".join([f"{k}: {v}" for k, v in res.items()])))
            await bot.send(event, MessageSegment.image(image))
            _id = "pixiv_" + res["id"].__str__()
            _id_with_format = f"{_id}.jpeg"
            await _up_exist()

        else:
            _user_id = str(event.user_id)[:4]  # 取用户qq前四位用作随机图片名上半段
            res = await saucenao_search(image, _config["saucenao_api"], "http://127.0.0.1:7890")

            if res.status_code // 100 == 2:
                if res.content["index"] == "pixiv":
                    logger.warning(res.content)
                    _id = "pixiv_" + res.content["data"]["illust_id"].__str__()
                    _id_with_format = f"{_id}.jpeg"
                    _response.content = f"发现pixiv原图, illust_id: {res.content['data']['illust_id'].__str__()}\n"
                    await _up_exist()
                elif res.content["index"] == "twitter":
                    tweet_id = str(res.content["data"]["url"]).split("/")[-1]
                    _id = f"twitter_{tweet_id}"
                    _id_with_format = f"{_id}.jpeg"
                    _response.content = f"发现twitter原图, illust_id: {tweet_id}\n"
                    logger.error(_id)
                    await _up_exist()
                elif res.content["index"] == "danbooru":
                    if "twitter" in res.content["data"]["source"]:
                        tweet_id = str(res.content["data"]["source"]).split("/")[-1]
                        _id = f"twitter_{tweet_id}"
                        _id_with_format = f"{_id}.jpeg"
                        _response.content = f"发现twitter原图, illust_id: {tweet_id}\n"
                        logger.error(_id)
                        await _up_exist()
                    else:
                        await _up_user()
                else:
                    await _up_user()

            else:
                await _up_user()


@uploadMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    images = await get_message_image(data=event.json(), type="file")
    if images:
        matcher.set_arg("images", images)
    elif pids := args.extract_plain_text().split():
        matcher.set_arg("images", pids)


@uploadMatcher.got("images", prompt="你想传什么夸图呢")
async def _(event: MessageEvent, images: list = Arg("images")):
    logger.warning(images)
    """aqua bot upload
    """
    if not images:
        await searchMatcher.reject(MessageSegment.text("发张图?"))

    if isinstance(images, Message):
        images = await get_message_image(data=event.json(), type="file")
        if not images:
            images = event.message.extract_plain_text().split()
    await searchMatcher.send(MessageSegment.text("正在传"))
    logger.warning(images)
    for image in images:
        await upload_aqua(get_bot(), event, image)


async def delete_aqua(bot: Bot, event: MessageEvent, image: str):
    """删除一张夸图
    """
    res = await db.delete(image)
    answer = MessageSegment.reply(event.message_id) + MessageSegment.text(res.message)
    await bot.send(event, answer)


@deleteMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if images := args.extract_plain_text().split():
        matcher.set_arg("images", images)


@deleteMatcher.got("images", prompt="你想删什么图呢? 回复夸图`id`可查看这张图的id")
async def _(event: MessageEvent, images: list = Arg("images")):
    if isinstance(images, Message):
        images = event.message.extract_plain_text().split()
    if not images:
        deleteMatcher.reject("图来!")
    for image in images:
        await delete_aqua(get_bot(), event, image)


async def debug(bot: Bot, event: Event):
    """!debug mode!
    """
    if not _config["debug"]:
        return await bot.send(event, MessageSegment.text("debug mode is off."))
    cmd = " ".join(args[1:])
    cmd = unescape(cmd)
    print(cmd)
    await bot.send(event, str(eval(cmd)))


async def func(bot: Bot, event: Event):
    """!debug mode!
    """
    if not _config["debug"]:
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
    return await bot.send(event, MessageSegment.text(_text["chinese"]["help"]))


@helpMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if arg := args.extract_plain_text():
        matcher.set_arg("arg", arg)


@helpMatcher.got("arg", prompt=_text["chinese"]["help_simple"])
async def _(event: MessageEvent, arg: str = Arg("arg")):
    if isinstance(arg, Message):
        arg = event.get_message().extract_plain_text()
    if arg not in ["random", "more", "help", "pixiv", "upload", "stats", "search", "delete","illust", "chat", "resetchat"]:
        await helpMatcher.reject("可选项: ['random','more','help','pixiv','upload','stats','search','delete','illust','chat','resetchat']")
    await helpMatcher.finish(MessageSegment.text(_text["chinese"][f"help_{arg}"]))


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


async def pixiv_aqua(bot: Bot, event: Event, args: list):
    logger.warning(args)

    _full = False

    if len(args) == 2:  # day 1
        dur, index = args
        word = "湊あくあ"
    elif len(args) == 3:  # day 1 full | word day 1
        if args[-1] == "full":  # day 1 full
            word = "湊あくあ"
            dur, index, _full = args
        else:  # word day 1
            word, dur, index = args
    elif len(args) == 4:  # word day 1 full
        word, dur, index, _full = args
    else:
        return await bot.send(event, MessageSegment.text("参 数 错 误"))

    if _full and _full == "full":
        _full = True
    elif _full:
        return await bot.send(event, MessageSegment.text("参 数 错 误"))

    word = word.replace("_", " ")

    _REQUESTS_KWARGS = {
        "proxies": {"https": "http://127.0.0.1:7890",},
    }
    res = await pixiv_search(
        refresh_token=_config["refresh_token"],
        word=word,
        search_target="partial_match_for_tags",
        # search_target="title_and_caption",
        sort="popular_desc",
        duration=dur,
        index=index,
        _REQUESTS_KWARGS=_REQUESTS_KWARGS,
        proxy="http://127.0.0.1:7890",
        full=_full,
    )
    await _pixiv_res_handle(bot, event, res)


@pixivMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if args_list := args.extract_plain_text().split():
        matcher.set_arg("args_list", args_list)


@pixivMatcher.got("args_list", prompt="参数来!")
async def _(event: MessageEvent, args: list = Arg("args_list")):
    if isinstance(args, Message):
        args = event.message.extract_plain_text().split()
    if not args:
        await pixivMatcher.reject("参数来!")
    await pixiv_aqua(get_bot(), event, args)


@moreMatcher.handle()
async def _(bot: Bot, event: MessageEvent):
    return await more_aqua(bot, event)


async def more_aqua(bot: Bot, event: Event):
    for _ in range(randint(2, 4)):
        key, image = (await db.get_random()).content
        id = await bot.send(event, MessageSegment.image(image))
        record_id(id, key)


async def reload_aqua():
    return db.reload()


@catMatcher.handle()
async def _(bot: Bot, event: MessageEvent):
    if event.message_type =="group":
        if event.group_id not in _config["cat_detect_group"]:
            return
    else:
        if event.user_id not in _config["cat_detect_private"]:
            return

    images = await get_message_image(data=event.json(), type="file")
    if images:
        for image in images:
            res = await cat_detect(_config["cat_detect_url"], image, "http://127.0.0.1:7890")
            if res.status_code == ACTION_SUCCESS:
                await bot.send(event, MessageSegment.image(res.content))
            

@reloadMatcher.handle()
async def _():
    await reload_aqua()


@replySearchMatcher.handle()
async def _(bot: Bot, event: MessageEvent):
    if not (r := re_search(r"\[CQ:reply,id=(-?\d*)]", event.raw_message)):
        return
    if (event.self_id == event.reply.sender.user_id) and ("id" in event.get_plaintext()):
        await bot.send(
            event,
            MessageSegment.reply(event.user_id) + MessageSegment.text(db.get_picture_id(event.reply.message_id)),
        )
    elif event.get_plaintext() in ["搜", "aquasearch", "aqua search", "search"]:
        msg = await bot.get_msg(message_id=event.reply.message_id)
        images = await get_message_image(msg, type="file")
        if images:
            await bot.send(event, MessageSegment.text("正在搜"))
        for image in images:
            print(f"image:{image}")
            await _search_handle(image, event)


@pokeMatcher.handle()
async def _(bot: Bot, event: PokeNotifyEvent):
    if event.self_id == event.target_id:
        return await random_aqua(bot, event)


async def stats_aqua(bot: Bot, event: Event):
    """统计
    """
    message = MessageSegment.text(f"一共有{db.db['total_count']}张夸图\n还能随机{db.db['available_count']}张")
    await bot.send(event, message)


@statsMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    await stats_aqua(get_bot(), event)


async def save_aqua(bot: Bot, event: Event):
    db.save()


@saveMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    await save_aqua(get_bot(), event)

@resetChatMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    resp = ChatBot.reset_chat(event.user_id)
    bot = get_bot()
    await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(resp.message))


async def chat_aqua(bot: Bot, event: Event, text:str):
    cd_id = event.user_id
    resp = await ChatBot.chat(cd_id, text)

    return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(resp.message))
    

@chatMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if text := args.extract_plain_text():
        matcher.set_arg("text", text)

@chatMatcher.got("text", prompt="说点什么吧")
async def _(event: MessageEvent, text: str = Arg("text")):
    if isinstance(text, Message):
        args = event.message.extract_plain_text()
    if not text:
        await pixivMatcher.reject("说点什么吧")
    await chat_aqua(get_bot(), event, text)


@searchMatcher.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    images = await get_message_image(data=event.json(), type="file")
    if images:
        matcher.set_arg("images", images)


@searchMatcher.got("images", prompt="你想搜什么图呢")
async def search_aqua(event: MessageEvent, images: list = Arg("images")):
    """saucenao search module
    """
    if isinstance(images, Message):
        images = await get_message_image(data=event.json(), type="file")
    if not images:
        await searchMatcher.reject(MessageSegment.text("发张图?"))
    await searchMatcher.send(MessageSegment.text("正在搜"))
    for image in images:
        await _search_handle(image, event)


async def _search_handle(image, event):
    bot = get_bot()
    res = await saucenao_search(image, _config["saucenao_api"], "http://127.0.0.1:7890")
    logger.warning(res.status_code)
    logger.warning(res.content)
    if res.status_code // 100 == 2:
        _s = f"index: {res.content['index']}\nrate: {res.content['rate']}\n" + "\n".join(
            [f"{k}: {v}" for k, v in res.content["data"].items()]
        )

        await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s))
    else:
        a = Ascii2D()
        res: Response = await a.search(image)

        if res.status_code // 100 == 2:
            _s = "\n".join([f"{k}: {v}" for k, v in res.content.items()])
            return await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s))
        elif res.status_code == 300:
            _s1 = "\n".join([f"{k}: {v}" for k, v in res.content[0].items()])
            _s2 = "\n".join([f"{k}: {v}" for k, v in res.content[2].items()])
            image1 = (await _safe_get_image(res.content[1], proxies="http://127.0.0.1:7890")).content
            image2 = (await _safe_get_image(res.content[3], proxies="http://127.0.0.1:7890")).content
            await bot.send(
                event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s1) + MessageSegment.image(image1)
            )
            await bot.send(
                event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s2) + MessageSegment.image(image2)
            )
        elif res.status_code == 301:
            _s1 = "\n".join([f"{k}: {v}" for k, v in res.content[0].items()])
            image1 = (await _safe_get_image(res.content[1], proxies="http://127.0.0.1:7890")).content
            await bot.send(
                event, MessageSegment.reply(event.message_id) + MessageSegment.text(_s1) + MessageSegment.image(image1)
            )

        elif res.status_code // 100 == 4:
            await bot.send(event, MessageSegment.reply(event.message_id) + MessageSegment.text(res.message))
            # await bot.send(event, MessageSegment.at(_config["superuser"]))


# 每日一夸


@scheduler.scheduled_job("cron", hour=17, minute=46, second=10)
async def daily_aqua():
    _REQUESTS_KWARGS = {
        "proxies": {"https": "http://127.0.0.1:7890",},
    }
    bot = get_bot()
    info, image = (
        await pixiv_search(
            refresh_token=_config["refresh_token"],
            word="湊あくあ",
            search_target="partial_match_for_tags",
            sort="popular_desc",
            duration="day",
            index=1,
            _REQUESTS_KWARGS=_REQUESTS_KWARGS,
            proxy="http://127.0.0.1:7890",
            full=True,
        )
    ).content
    _text = MessageSegment.text(f"#每日一夸#\n{info['title']}\n♡: {info['bookmark']}  pid: {info['id']}")
    for group in _config["daily"]:
        await asyncio_sleep(1)
        print(type(image))
        print(image)
        await bot.call_api("send_group_msg", **{"group_id": group, "message": _text})
        await bot.call_api("send_group_msg", **{"group_id": group, "message": MessageSegment.image(image)})
