import json
import operator
from typing import Literal
import httpx
from loguru import logger
import pixivpy3 as pixivpy
from .response import *
from io import BytesIO

Response=BaseResponse

class Api():
    def __init__(self, refresh_token:str,**REQUEST_KWARGS):
        self.api = pixivpy.AppPixivAPI(**REQUEST_KWARGS) # app api
        self.api.set_accept_language('zh-CN,zh;q=0.9')
        self.api.auth(refresh_token=refresh_token)



async def pixiv_search(refresh_token:str, word:str, search_target:Literal['partial_match_for_tags','exact_match_for_tags','title_and_caption'], sort:str, duration:str,index,_REQUESTS_KWARGS=None,proxy=None,full=False)->Response:
    """对指定关键词搜索, 施加限定条件, 返回图片, 详见pixivpy3.search_illust  
    Args:    
    * ``refresh_token: str ``: pixiv登陆token  
    * ``word: str``: 搜索关键词  
    * ``search_target: Literial['partial_match_for_tags','exact_match_for_tags']``: 搜索类型,全字匹配或部分匹配
    * ``sort: str`` : 排序方式
    * ``duration: str``: 区间, 最近一日, 最近一周,最近一月...
    * ``index: int``: 希望取得的排行第几位的图片
    * ``_REQUESTS_KWARGS: dict``: http请求参数, 代理
    * ``proxy: str``: 代理
    * ``full: bool``: 是否返回原图, 默认返回large
    
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
    #print(res_json)
    illust_list = []
    for illust in res_json.illusts:
        if "origin_image_url" in illust.meta_single_page:
            origin = illust.meta_single_page["origin_image_url"]
        elif "original_image_url" in illust.meta_single_page:
            origin = illust.meta_single_page["original_image_url"]
        else:
            origin = illust.meta_pages[0]["image_urls"]["original"] # 当图集时， 取图集的第一个
    
        illust_list.append({"title":illust.title, "id":illust.id, "bookmark":int(illust.total_bookmarks), "large_url":illust.image_urls["large"], "origin":origin})
    illust_list.sort(key=operator.itemgetter("bookmark"), reverse=True)
    #illust_list = sorted([{"title": illust.title, "id": illust.id, "bookmark": int(illust.total_bookmarks), "large_url": illust.image_urls["large"],"origin": illust.meta_single_page["original_image_url"] if ("original_image_url" in illust['meta_single_page']) else illust.meta_single_page["origin_image_url"] } for illust in res_json.illusts],key=operator.itemgetter("bookmark"),reverse=True)
    if index > len(illust_list) or index < 1:
        return Response(ACTION_FAILED, f"Index out of range({len(illust_list)})", )
    if full:
        res = await get_pixiv_image(illust_list[index-1]['origin'],proxy)
    else:
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


    _retry = 3
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxies) as client:
                res = await client.get(url, headers=headers, timeout=5)
                #res.raise_for_status()
                return Response(ACTION_SUCCESS, content=BytesIO(res.content))

        except Exception as e:
            print(e)
            _retry -= 1
            if _retry == 0:
                return Response(ACTION_FAILED, message="下载图片出现错误, 请稍后再试")
    

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
    #print(illust_info)
    #print(type(illust_info))
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

async def get_pixiv_image_by_id(id:str, proxy=None) -> Response:
    """从hibiApi获取图片信息

    Args:
        id (str): pid
        proxy (_type_, optional): 代理. Defaults to None.

    Returns:
        Response: 
    """
    url = "https://api.obfs.dev/api/pixiv/illust?id=" + id
    logger.warning(url)
    async with httpx.AsyncClient(proxies=proxy) as client:
        res = await client.get(url, timeout=5)
        logger.warning(res)
        if res.status_code == 200:
            return Response(ACTION_SUCCESS, content=json.loads(res.content))
        return Response(ACTION_FAILED,message="请求上游api失败")
