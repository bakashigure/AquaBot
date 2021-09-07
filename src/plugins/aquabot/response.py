ACTION_SUCCESS = 200
ACTION_WARNING = 300
ACTION_FAILED = 400

class BaseResponse:
    """自定义返回 

    >>> code(int): 状态码
    >>> msg(str): 返回信息
    >>> content(any): 返回内容
    """

    def __init__(self, code, msg=None, content=None) -> None:
        self.code = code
        self.msg = msg
        self.content = content
        self.log = f"{self.code} | {self.msg}"
