from logging import log
import sys
from pydantic import BaseSettings
import nonebot
from nonebot import get_driver
from pathlib import Path
from nonebot.log import logger
import oss2


class Config(BaseSettings):
    shuffle_timeout: int = 10800

    class Config:
        extra = "ignore"


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

_config = dict()  # 读取配置

_help_url = "https://example.com"


def prehandle():
    global _help_url
    _config['storage'] = global_config.aqua_bot_pic_storage

    # 检测存储方式为本地或者oss
    if _config['storage'] == "local":
        _config['dir'] = global_config.aqua_bot_pic_dir
        if _config['dir']:  # 是否配置存储路径
            dir_path = Path(_config['dir']).absolute()  # 获取绝对路径
            if not Path(dir_path).is_dir():
                logger.error("路径%s不存在, 请手动创建"%dir_path)
                exit()
            _config['dir'] = dir_path
        else:
            logger.warning("本地存储路径未配置, 默认存放于bot根目录下src/plugins/aquabot/img目录")
            logger.warning("配置详见%s" % _help_url)
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
                logger.error("您选择了%s的图片存储方式" % _config['storage'],)
                logger.error(
                    "但 aqua_bot_oss_%s 未设置, 请检查.env文件, 配置详见 %s" % (k, _help_url))
                exit()
               

       
        _config['auth']=oss2.Auth(_config['access_key_id'], _config['access_key_secret'])
        _config['bucket']=oss2.Bucket(_config['auth'],_config['endpoint'], _config['bucket'])
        _config['service']= oss2.Service(_config['auth'], _config['endpoint'])

        try:
            logger.info("检测oss连通性...")
            _config['service'].list_buckets()
            logger.info("oss连通性测试成功")
        except oss2.exceptions.ServerError as e:
            if e.status == 403:
                logger.error("连接OSS时发生权限错误, 请检查access_key_id和access_key_secret是否正确")
                exit()
        except Exception as e:
            logger.error(e)
            logger.error("连接OSS时发生错误, 详见 https://help.aliyun.com/document_detail/32039.html")
            exit()

    else:
        _help_url = ""
        logger.error("存储方式不正确, 请检查.env文件, 有关配置详见%s " % _help_url)
        exit()

    _config['pixiv']=True
    _config['refresh_token'] = global_config.aqua_bot_pixiv_refresh_token
    if _config['refresh_token'] == "" or None:
        logger.warning("没有设置pixiv refresh token, pixiv相关功能将不可用")
        _config['pixiv']=False


    _config['saucenao_api'] = global_config.AQUA_BOT_SAUCENAO_API
    _config['saucenao']=True
    logger.error(type(global_config.AQUA_BOT_SAUCENAO_API))
    logger.error(_config['saucenao_api'])
    logger.error(type(_config['saucenao_api']))
    if _config['saucenao_api'] == None:
        logger.warning("没有设置saucenao api, 搜图相关功能将不可用")
        _config['saucenao']=False


    return _config
