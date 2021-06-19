from pydantic import BaseSettings
import nonebot
from nonebot import get_driver

class Config(BaseSettings):
    AQUA_BOT_OSS_ACCESS_KEY_ID=""

    class Config:
        extra = "ignore"

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())


