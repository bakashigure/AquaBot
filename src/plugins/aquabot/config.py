from pydantic import BaseSettings
import nonebot
from nonebot import get_driver


class Config(BaseSettings):
    shuffle_timeout: int = 10800
    
    class Config:
        extra = "ignore"


misc=dict()


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())


