# @Author: bakashigure 
# @Date: 2022-01-31 14:43:26 
# @Last Modified by:   bakashigure 
# @Last Modified time: 2022-01-31 14:43:26 

import json
from copy import deepcopy
from email.utils import formatdate
from json.decoder import JSONDecodeError
from os import remove as os_remove
from os import walk as os_walk
from pathlib import Path
import typing
from random import randint

from nonebot import get_driver
from nonebot.log import logger

from .config import Config, _config
from .response import BaseResponse as Response
from .utils import (
    ACTION_FAILED,
    ACTION_SUCCESS,
    ACTION_WARNING,
    get_message_image,
    get_path,
)
from .utils import upload_to_local

global_config = get_driver().config
plugin_config = Config(**global_config.dict())


class DB:
    """
    {
      "AquaBot": "this file created by aqua bot, please do not modify this file",
      "last_update": "",
      "records": "",
      "version":"",
      "local": {
            {"pixiv_114514","E://path//pixiv_114514.jpg"},
            {"pixiv_1919810","E://path//pixiv_1919810.jpg"},
            {"114514_4gaw89", "E://path//114514_4gaw89.png"}
      },
      "oss": {} ,
      "used": {}
    }
    """
    def __init__(self) -> None:
        self.db: dict  # 本体
        self.db_keys: list = []
        self.type = _config["storage"]  # 存储类型, 'oss' or 'local'
        self.record_file = _config["database"]  # 记录文件路径
        self.messages: typing.Dict[str, str] = {}

        self.__version__ = "1.0.0"  # db version

        """
        if self.type == "oss":
            self.auth = oss2.Auth(
                _config["access_key_id"], _config["access_key_secret"]
            )
            self.bucket = oss2.Bucket(self.auth, _config["endpoint"], _config["bucket"])
        """
        # 从配置文件中读取夸图数据库, 避免读取本地文件或者oss造成缓慢性能
        # 如果配置文件不存在则生成一个
        try:
            with open(self.record_file, "r") as f:
                self.db = json.load(f)
                logger.info("loaded db")
                # print("DB: %s" % self.db)

        except FileNotFoundError:
            logger.warning(f"record file not set, will create in {self.record_file}")
            init_content = r' { "AquaBot": "this file created by aqua bot, please do not modify this file", "last_update":"", "records":"", "version":"", "total_count":0,"local":{}, "oss":{},"available_count":0,"available":{},"used_count":0,"used":{} }'
            with open(self.record_file, "w") as f:
                f.write(init_content)
            self.db = json.loads(init_content)
            self.reload()
            self.db["version"] = self.__version__
            self.last_update()
            # logger.warning("DB: %s" % self.db)
            self.save()

        except JSONDecodeError as e:
            logger.error(f"JSON decode error -> {e}")
            exit()

        self.refresh()

    def refresh(self) -> Response:
        """把发过的图片重新添加到图库
        """
        self.db["available"].update(self.db["used"])
        self.db["used"] = {}
        self.db_keys = list(self.db[self.type].keys())
        self.db["total_count"] = len(self.db_keys)
        self.db["available_count"] = self.db["total_count"]
        self.db["used_count"] = 0
        self.last_update()
        return Response(
            ACTION_SUCCESS, f'refresh success, db_total:{self.db["total_count"]}'
        )

    def reload(self) -> Response:
        """清空配置, 重新读取本地文件或oss.
        """
        self.db["oss"] = {}
        self.db["local"] = {}
        self.db["used"] = {}
        if self.type == "local":
            for _, _, files in os_walk(_config["dir"]):
                [self.add_record(f, Path(_config["dir"]).joinpath(f).as_posix()) for f in files]
        else:
            # TODO READ OSS FILE LIST
            # OSS2.LISTOBJECTSV2
            ...

        self.db["available"] = deepcopy(self.db[self.type])
        self.refresh()
        return Response(ACTION_SUCCESS, "reload success")

    def last_update(self) -> Response:
        """更新'last_update'字段
        """
        self.db["last_update"] = formatdate(usegmt=False)
        return Response(ACTION_SUCCESS, f'last_update: {self.db["last_update"]}')

    def save(self) -> Response:
        """保存数据库到本地文件
        """

        with open(self.record_file, "w") as f:
            f.write(json.dumps(self.db))

        return Response(ACTION_SUCCESS, "save success")

    async def upload(self, *args, **kwargs):
        """添加一个夸图到数据库

        :origin: 夸图原图路径
        """
        if self.type == "local":
            res = upload_to_local(*args, **kwargs)
            if res.status_code // 100 == 2:
                self.add_record(*res.content)
            return res

    def add_record(self, k, v) -> Response:
        if k not in self.db[self.type]:
            self.db["total_count"] += 1
        self.db[self.type][k] = v
        return Response(ACTION_SUCCESS, f"add_record record: {k} -> {v}")

    async def delete(self, k: str) -> Response:

        try:
            k = k
            print(k)
            print(k in self.db[self.type])
            os_remove(self.db[self.type][k])
        except Exception as e:
            return Response(ACTION_FAILED, "图 片 不 存 在")

        try:
            del self.db[self.type][k]
        except:
            pass
        try:
            del self.db["available"][k]
        except:
            pass
        try:
            del self.db["used"][k]
        except:
            pass

        return Response(ACTION_SUCCESS, f"已删除{k}")

    @classmethod
    def set_type(cls, _type) -> None:
        cls.type = _type

    def exist(self, k) -> bool:
        return k in self.db[self.type]

    async def get_random(self) -> Response:
        if self.db["available_count"] == 0:
            Response(ACTION_FAILED, "No record available, will refresh records")
            self.refresh()  # 即刻触发refresh
            if self.db["total_count"] == 0:
                return Response(ACTION_FAILED, message="No record available, please upload some pictures :)",)
        choice = randint(0, self.db["available_count"] - 1)
        key = self.db_keys[choice]
        del self.db_keys[choice]
        value = self.db["available"][key]

        self.db["used"][key] = value
        self.db["used_count"] += 1

        del self.db["available"][key]
        self.db["available_count"] -= 1

        if _config["storage"] == "local":
            value = f"file:///{value}"
        return Response(ACTION_SUCCESS, message="Get a random picture.", content=(key, f"{value}"))

    def get_picture_id(self, k):
        k = str(k)
        return self.messages[k]
