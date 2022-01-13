#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
from nonebot.adapters.onebot.v11 import Adapter


# Custom your logger
# 
# from nonebot.log import logger, default_format
# logger.add("error.log",
#            rotation="00:00",1
#            diagnose=False,
#            level="ERROR",
#            format=default_format)

# You can pass some keyword args config to init function
nonebot.init(_env_file=".env")
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

#nonebot.load_builtin_plugins()
#nonebot.load_plugin("src.plugins.aquabot.uu")
#nonebot.load_plugin("nonebot_plugin_test")
nonebot.load_plugin("src.plugins.aquabot")

#nonebot.load_from_toml(".pyproject.toml")

# Modify some config / config depends on loaded configs
# 
# config = driver.config
# do something...


nonebot.run()