import operator
from typing import Literal
import httpx
import pixivpy3 as pixivpy
from .response import *
from io import BytesIO

Response=BaseResponse

class Api():
    print("call api")
    __instance = None
    api = None
    def __new__(cls, refresh_token,**_REQUESTS_KWARGS):
        print("call new")
        if cls.__instance is None:
            print("call new instance")
            cls.__instance = object.__new__(cls)
            cls.api = pixivpy.AppPixivAPI(**_REQUESTS_KWARGS)
            cls.api.set_accept_language("en_us") 
            cls.api.auth(refresh_token=refresh_token)
        return cls.__instance




async def pixiv_search(refresh_token:str, word:str, search_target:Literal['partial_match_for_tags','exact_match_for_tags'], sort:str, duration:str,index,_REQUESTS_KWARGS=None,proxy=None)->Response:
    """对指定关键词搜索, 施加限定条件, 返回图片, 详见pixivpy3.search_illust  
    Args:    
    * ``refresh_token: str ``: pixiv登陆token  
    * ``word: str``: 搜索关键词  
    * ``search_target: Literial['partial_match_for_tags','exact_match_for_tags']``: 搜索类型,全字匹配或部分匹配
    * ``sort: str`` : 排序方式
    * ``duration: str``: 区间, 最近一日, 最近一周,最近一月...
    * ``index: int``: 希望取得的排行第几位的图片
    * ``_REQUESTS_KWARGS: dict``: http请求参数, 代理
    
    代理模板:
    >>> _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
  

    Returns:  
    * ``Response.status_code: int``: 状态码
    * ``Response.content: tuple(dict,BytesIO))``: 图片信息, 图片对象
    * ``Response.message: str``: 信息
    """
    

    api = Api(refresh_token,**_REQUESTS_KWARGS).api

    if duration not in ["day", "week", "month"]:    
        return Response(ACTION_FAILED, message = "Invalid duration")
    try:
        index=int(index)
    except ValueError:
        return Response(ACTION_FAILED, message = "Invalid index")
        
    duration = "within_last_" + duration
    res_json = api.search_illust(word, search_target, sort, duration)
    illust_list = sorted([{"title": illust.title, "id": illust.id, "bookmark": int(illust.total_bookmarks), "large_url": illust.image_urls["large"]} for illust in res_json.illusts],key=operator.itemgetter("bookmark"),reverse=True)
    if index > len(illust_list) or index < 1:
        return Response(ACTION_FAILED, f"Index out of range({len(illust_list)})", )
    
    res = await get_pixiv_image(illust_list[index-1]["large_url"],proxy)
    if res.status_code // 100 != 2:
        return Response(ACTION_FAILED, message=f"{res.message}")
    else:
        return Response(ACTION_SUCCESS, content=(illust_list[index-1],res.content))

async def _safe_get_image(url: str, headers: dict = None, proxies: str = None) -> Response:
    """
    下载图片, 并返回图片对象

    Args :
        * ``url: str``: 图片url
        * `` headers: dict``: 请求头
        * `` proxies: str``: 代理

    Returns :
        * `` Response.status_code: int`` : 请求的状态码
        * `` Response.content: Image.Image`` : 图片
        * `` Response.message: str`` : 请求失败的原因
    """
    try:
        async with httpx.AsyncClient(proxies=proxies) as client:
            res = await client.get(url, headers=headers, timeout=5)
            res.raise_for_status()
    except httpx.ProxyError as exc:
        return Response(ACTION_FAILED,message="httpx proxy error.")
    except httpx.HTTPStatusError as exc:
        return Response(ACTION_FAILED,message=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
    return Response(ACTION_SUCCESS, content=BytesIO(res.content))


async def get_pixiv_image_by_pid(pid,refresh_token,_REQUESTS_KWARGS=None,proxies=None)->Response:
    """
    通过pid获取图片

    Args:
    * ``pid: str``: pixiv图片id
    * ``refresh_token: str``: pixiv登陆token
    * ``_REQUESTS_KWARGS: dict``: http请求参数, 代理
    * ``proxies: str``: 代理

    代理模板:
    >>> _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
    
    Returns:
    * ``Response.status_code: int``: 状态码
    * ``Response.content: (dict,Image.Image)``: 图片信息和图片对象
    """
    api = Api(refresh_token,**_REQUESTS_KWARGS).api
    illust_info = api.illust_detail(pid)
    print(illust_info)
    print(type(illust_info))
    _info = {"title":illust_info['illust']['title'],"♡":illust_info['illust']['total_bookmarks'],"id":illust_info['illust']['id']}
    _image = await get_pixiv_image(illust_info["illust"]["image_urls"]["large"],proxies)
    return Response(ACTION_SUCCESS,content=(_info,_image.content))


async def get_pixiv_image(url: str, proxy=None) -> Response:
    """
    下载一张pixiv图片, 会带上pixiv请求头, 返回图片对象

    Args :
        * `` url: str`` : 图片url
        * `` proxies: str`` : 代理(可选)

    Returns:
        * `` Response.status_code: int`` : 请求的状态码
        * `` Response.content: Image.Image`` : 图片
        * `` Response.message: str`` : 请求失败的原因
    """
    headers = {"Referer": "https://www.pixiv.net/"}
    return await _safe_get_image(url, headers, proxy)