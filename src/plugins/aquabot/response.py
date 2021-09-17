from typing import Any


ACTION_SUCCESS = 200
ACTION_WARNING = 300
ACTION_FAILED = 400

class BaseResponse:
    """AQUABOT 返回类

    * `` 当操作正常, 返回 ACTION_SUCCESS message , content`` 
    * `` 当操作异常, 返回 ACTION_WARNING 和message``
    * `` 当操作失败, 返回 ACTION_FAILED 和message``

    * ``status_code: int`` : 状态码
    * ``message: str`` : 信息
    * ``content: any`` : 返回内容
    """

    def __init__(self, status_code:int, message:str=None, content:Any=None) -> None:
        self.status_code = status_code
        self.message = message
        self.content = content
        self.log = f"{self.status_code} | {self.message}"
