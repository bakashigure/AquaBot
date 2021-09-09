from typing import Any


ACTION_SUCCESS = 200
ACTION_WARNING = 300
ACTION_FAILED = 400

class BaseResponse:
    """AQUABOT 返回类
    >>> 当操作正常, 返回 ACTION_SUCCESS 和 content
    >>> 当操作异常, 返回 ACTION_WARNING | ACTION_FAILED 和message

    >>> status_code(int): 状态码
    >>> message(str): 错误信息
    >>> content(any): 返回内容
    """

    def __init__(self, status_code, message=None, content:Any=None) -> None:
        self.status_code = status_code
        self.message = message
        self.content = content
        self.log = f"{self.status_code} | {self.message}"
