import operator
from httpx import AsyncClient
import pixivpy3 as pixivpy
from .utils import Response, get_pixiv_image
from .response import *

Response=BaseResponse

async def pixiv_search(refresh_token:str, word:str, search_target:str, sort:str, duration:str,index,_REQUESTS_KWARGS=None,proxy=None)->Response:
    """对指定关键词搜索, 施加限定条件, 返回图片, 详见pixivpy3.search_illust

    Args:
    >>> refresh_token(str): pixiv登陆token
    >>> word(str): 关键词
    >>> search_target(str): 搜索类型,全字匹配或部分匹配
    >>> sort(str): 排序方式
    >>> duration(str): 区间, 最近一日, 最近一周,最近一月...
    >>> index(int): 希望取得的排行第几位的图片
    >>> _REQUESTS_KWARGS(dict): http请求参数, 代理
    
    代理模板::
    >>> _REQUESTS_KWARGS = {
        'proxies': {
            'https': 'http://127.0.0.1:7890',
        }, }
  

    Returns:
    >>> Response.status_code(int): 状态码
    >>> Response.content(tuple[dict,Image.Image]): 图片信息, 图片对象
    >>> Response.message(str): 错误信息
    """
    

    api = pixivpy.AppPixivAPI(**_REQUESTS_KWARGS)
    api.set_accept_language("en_us")
    try:
        api.auth(refresh_token=refresh_token)
    except Exception as e:
        return Response(ACTION_FAILED, "Pixiv auth failed: {}".format(e))

    if duration not in ["day", "week", "month"]:    
        return Response(ACTION_FAILED, "Invalid duration")
    try:
        index=int(index)
    except ValueError:
        return Response(ACTION_FAILED, "Invalid index")
        
    duration = "within_last_" + duration
    res_json = api.search_illust(word, search_target, sort, duration)
    illust_list = sorted([{"title": illust.title, "id": illust.id, "bookmark": int(illust.total_bookmarks), "large_url": illust.image_urls["large"]} for illust in res_json.illusts],key=operator.itemgetter("bookmark"),reverse=True)
    if index > len(illust_list) or index < 1:
        return Response(ACTION_FAILED, f"Index out of range({len(illust_list)})", )
    
    res = await get_pixiv_image(illust_list[index-1]["large_url"],proxies=proxy)
    if res.status_code // 100 != 2:
        return Response(ACTION_FAILED, message=f"{res.message}")
    else:
        return Response(ACTION_SUCCESS, content=(illust_list[index-1],res.content))