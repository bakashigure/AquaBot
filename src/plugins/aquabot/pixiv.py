import operator
from httpx import AsyncClient
import pixivpy3 as pixivpy
from .utils import Response, get_pixiv_image
from .response import *

Response=BaseResponse

async def pixiv_search(refresh_token:str, word:str, search_target:str, sort:str, duration:str,index):
    """对指定关键词搜索, 施加限定条件, 返回图片

    Args:
    >>> refresh_token(str): pixiv登陆token
    >>> word(str): 关键词
    >>> search_target(str): 搜索类型,全字匹配或部分匹配
    >>> sort(str): 排序方式
    >>> duration(str): 区间, 最近一日, 最近一周,最近一月...
    >>> index(int): 希望取得的排行第几位的图片

    Returns:
    """
    

    api = pixivpy.AppPixivAPI()
    api.set_accept_language("en_us")
    try:
        api.auth(refresh_token=refresh_token)
    except Exception as e:
        return Response(ACTION_FAILED, "Pixiv auth failed: {}".format(e))

    if duration not in ["day", "week", "month"]:    
        return Response(ACTION_FAILED, "Invalid duration")
    
    duration = "within_last_" + duration
    res_json = api.search_illust(word, search_target, sort, duration)
    illust_list = sorted([{"title": illust.title, "id": illust.id, "bookmark": int(illust.total_bookmarks), "large_url": illust.image_urls["large"]} for illust in res_json.illusts],key=operator.itemgetter("bookmark"),reverse=True)
    if index > len(illust_list):
        return Response(ACTION_FAILED, f"Index out of range({len(illust_list)})", )
    
    res = await get_pixiv_image(illust_list[index-1]["large_url"])
    if res.code // 100 != 2:
        return Response(ACTION_FAILED, f"Get image failed: {res.msg}")
    else:
        return Response(ACTION_SUCCESS, res.content)