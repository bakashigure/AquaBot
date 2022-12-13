from logging import log
import sys
from pydantic import BaseSettings
import nonebot
from nonebot import get_driver
from pathlib import Path
from nonebot.log import logger
#import oss2
logger.warning("importing config...")


class Config(BaseSettings):
    class Config:
        extra = "ignore"


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

_help_url = "https://example.com"

_config = {"debug": global_config.aqua_bot_debug.lower() == "true"}
# proxy
if len(global_config.aqua_bot_global_proxy) > 0:
    _config['proxy'] = global_config.aqua_bot_global_proxy
else:
    _config['proxy'] = None
_config['cqhttp'] = Path(global_config.cqhttp).resolve()
_config['storage'] = global_config.aqua_bot_pic_storage
_config['database'] = Path(global_config.aqua_bot_database).resolve()
_config['cache'] = Path(global_config.aqua_bot_pic_cache_dir).resolve()

# 发送每日一夸的群组
_config['daily'] = list(global_config.aqua_bot_groups_daily)

# 进行一个cqhttp地址的检测, 因为需要读取图片
if not _config['cqhttp']:
    logger.error("未设置cqhttp路径, 请修改.env文件")
    exit()

_config['superuser'] = global_config.superuser
# 检测存储方式为本地或者oss
if _config['storage'] == "local":
    _config['dir'] = global_config.aqua_bot_pic_dir
    if _config['dir']:  # 是否配置存储路径
        dir_path = Path(_config['dir']).absolute()  # 获取绝对路径
        if not Path(dir_path).is_dir():
            logger.error(f"路径{dir_path}不存在, 请手动创建")
            exit()
        _config['dir'] = dir_path
    else:
        logger.warning("本地存储路径未配置, 默认存放于bot根目录下src/plugins/aquabot/img目录")
        logger.warning(f"配置详见{_help_url}")
        _config['dir'] = "src/plugins/aquabot/img"
        _config['dir'] = Path(_config['dir']).absolute()
elif _config['storage'] == "oss":
    _config['access_key_id'] = global_config.aqua_bot_oss_access_key_id
    _config['access_key_secret'] = global_config.aqua_bot_oss_access_key_secret
    #_config['prefix'] = global_config.aqua_bot_oss_prefix
    _config['endpoint'] = global_config.aqua_bot_oss_endpoint
    _config['bucket'] = global_config.aqua_bot_oss_bucket
    for k, v in _config.items():
        if v == "":
            logger.error(f"您选择了{_config['storage']}的图片存储方式")
            logger.error(f"但 aqua_bot_oss_{k} 未设置, 请检查.env文件, 配置详见 {_help_url}")
            exit()

    # 暂时不打算再搞oss了(
    """
    _config['auth'] = oss2.Auth(
        _config['access_key_id'], _config['access_key_secret'])
    _config['bucket'] = oss2.Bucket(
        _config['auth'], _config['endpoint'], _config['bucket'])
    _config['service'] = oss2.Service(_config['auth'], _config['endpoint'])

    try:
        logger.info("检测oss连通性...")
        _config['service'].list_buckets()
        logger.info("oss连通性测试成功")
    except oss2.exceptions.ServerError as e:
        if e.status == 403:
            logger.error(
                "连接OSS时发生权限错误, 请检查access_key_id和access_key_secret是否正确")
            exit()
    except Exception as e:
        logger.error(e)
        logger.error(
            "连接OSS时发生错误, 详见 https://help.aliyun.com/document_detail/32039.html")
        exit()
        """
else:
    _help_url = ""
    logger.error(f"存储方式不正确, 请检查.env文件, 有关配置详见{_help_url} ")
    exit()

# pixiv refresh_token 相关
_config['pixiv'] = True
_config['refresh_token'] = global_config.aqua_bot_pixiv_refresh_token
if not _config['refresh_token']:
    logger.warning("没有设置pixiv refresh token, pixiv相关功能将不可用")
    _config['pixiv'] = False

# saucenao api 相关
_config['saucenao_api'] = global_config.aqua_bot_saucenao_api
_config['saucenao'] = True
if not _config['saucenao_api']:
    logger.warning("没有设置saucenao api, 搜图相关功能将不可用")
    _config['saucenao'] = False

# language相关
_config['language'] = global_config.aqua_bot_language
if _config['language'] not in ['aqua', 'chinese', 'english', 'japanese']:
    logger.error("language设置不正确, 请检查.env文件")


# gpt key
_config['chatgpt_session_token'] = global_config.chatgpt_session_token
_config['chat_cooldown'] = global_config.chat_cooldown