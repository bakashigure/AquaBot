# -*- coding:utf-8 -*-
# Modified from https://saucenao.com/tools/examples/api/identify_images_v1.1.py
# Created by bakashigure


import io
import json
import re
from collections import OrderedDict

import httpx
from PIL import Image, ImageFile

from .response import *

Response = BaseResponse


async def saucenao_search(file_path: str, APIKEY: str, proxy=None) -> Response:
    """saucenao search moudle

    Args:
    * ``file_path`` : target picture
    * ``APIKEY: str``: saucenao APIKEY (apply from https://saucenao.com/account/register)
    * ``proxy:str``: proxy (default: None)

    Returns:
    ``Response: Response``

    当搜索结果相似度小于75%时:
    >>> Response.status = ACTION_WARNING
    >>> Response.message:str #此api剩余搜索次数
    >>> Response.message:str #相似度信息

    当搜索结果相似度大于75%时:
    >>> Response.status = ACTION_SUCCESS
    >>> Response.message:str #此api剩余搜索次数
    >>> Response.content:dict #返回搜索结果字典

    其他情况:
    >>> Response.status = ACTION_FAILED
    >>> Response.message:str #错误信息
    """
    bitmask_all = '999' #搜索saucenao全部index
    default_minsim = '75!' #最小匹配相似度
    _message = {}
    ImageFile.LOAD_TRUNCATED_IMAGES = True #qq有时候拿到的是烂图, 不完整的
    image = Image.open(file_path)
    image = image.convert('RGB')
    thumbSize = (250, 250)
    image.thumbnail(thumbSize, resample=Image.ANTIALIAS)
    imageData = io.BytesIO()
    image.save(imageData, format='PNG')

    url_all = (
        (
            f'http://saucenao.com/search.php?output_type=2&numres=1&minsim={default_minsim}&db='
            + bitmask_all
        )
        + '&api_key='
    ) + APIKEY

    files = {'file': (file_path, imageData.getvalue())}
    imageData.close()

    _retry = 3
    r = None

    async with httpx.AsyncClient(proxies=proxy,follow_redirects=True) as client:
        try:
            r = await client.post(url=url_all, files=files)
        except httpx.ReadTimeout or httpx.ProxyError:
            return Response(ACTION_FAILED,"timeout")


    if r.status_code == 200:
        results = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
        if int(results['header']['user_id']) <= 0:
            # General issue, api did not respond. Normal site took over for this error state.
            # Issue is unclear, so don't flood requests.
            return Response(ACTION_FAILED, "Bad image or API failure. ")

        _remain_searches = 'Remaining Searches 30s|24h: ' + str( results['header']['short_remaining']) + '|' + str(results['header']['long_remaining'])
        print(_remain_searches)
        if int(results['header']['status']) == 0:
            # search succeeded for all indexes, results usable
            ...
        else:
            return (
                Response(ACTION_FAILED, "SauceNAO error, pls try again later.")
                if int(results['header']['status']) > 0
                else Response(
                    ACTION_FAILED, "Bad image or other request error. "
                )
            )

        if int(results['header']['results_returned']) > 0:
            artwork_url = ""
            print(results)
            rate = results['results'][0]['header']['similarity']+'%'
            if float(results['results'][0]['header']['similarity']) <= float(
                results['header']['minimum_similarity']
            ):
                return Response(ACTION_WARNING, message=f"rate: {rate}\nnot found... ;_;")


            print('hit! ' + str(results['results']
                                [0]['header']['similarity']))
            # print(results)
            # get vars to use
            #index = ''
            illust_id = 0
            member_id = -1
            index_id = results['results'][0]['header']['index_id']
            page_string = (
                page_match[1]
                if (
                    page_match := re.search(
                        '(_p[\d]+)\.',
                        results['results'][0]['header']['thumbnail'],
                    )
                )
                else ''
            )

            # print(results)
            #found_json = {"type": "success", "rate": "{0}%".format(str(results['results'][0]['header']['similarity'])), "data": {}}

            found_json = {'index':"",'rate':"",'data':{}}

            if index_id in [5, 6]:
                # 5->pixiv 6->pixiv historical
                found_json['index'] = "pixiv"
                member_name = results['results'][0]['data']['member_name']
                illust_id = results['results'][0]['data']['pixiv_id']
                title = results['results'][0]['data']['title']
                artwork_url = f"https://pixiv.net/artworks/{illust_id}"
                found_json['data'] = {"title": title, "illust_id": illust_id, "member_name": member_name,"url":artwork_url}

            elif index_id == 8:
                # 8->nico nico seiga

                found_json['index'] = 'seiga'
                member_id = results['results'][0]['data']['member_id']
                illust_id = results['results'][0]['data']['seiga_id']
                found_json['data'] = {"member_id": member_id, "illust_id": illust_id}
            elif index_id == 10:
                # 10->drawr
                found_json['index'] = 'drawr'
                member_id = results['results'][0]['data']['member_id']
                illust_id = results['results'][0]['data']['drawr_id']
                found_json['data'] = {"member_id": member_id, "illust_id": illust_id}
            elif index_id == 11:
                # 11->nijie
                found_json['index'] = 'nijie'
                member_id = results['results'][0]['data']['member_id']
                illust_id = results['results'][0]['data']['nijie_id']
                found_json['data'] = {"member_id": member_id, "illust_id": illust_id}
            elif index_id == 34:
                # 34->da
                found_json['index'] = 'da'
                illust_id = results['results'][0]['data']['da_id']
                found_json['data'] = {"illust_id": illust_id}
            elif index_id == 9:
                # 9 -> danbooru
                # index name, danbooru_id, gelbooru_id, creator, material, characters, sources
                found_json['index'] = "danbooru"
                creator = results['results'][0]['data']['creator']
                characters = results['results'][0]['data']['characters']
                source = results['results'][0]['data']['source']
                found_json['data'] = {"creator": creator, "characters": characters, "source": source}
            elif index_id == 38:
                # 38 -> H-Misc (E-Hentai)
                found_json['index'] = "H-Misc"
                source = results['results'][0]['data']['source']
                creator = results['results'][0]['data']['creator']
                if type(creator) == list:
                    creator = (lambda x: ", ".join(x))(creator)
                jp_name = results['results'][0]['data']['jp_name']
                found_json['data'] = {"source": source, "creator": creator, "jp_name": jp_name}
            elif index_id == 12:
                # 12 -> Yande.re
                # ext_urls, yandere_id, creator, material, characters, source
                found_json['index'] = "yandere"
                creator = results['results'][0]['data']['creator']
                if type(creator) == list:
                    creator = (lambda x: ", ".join(x))(creator)
                characters = results['results'][0]['data']['characters']
                source = results['results'][0]['data']['source']
                found_json['data'] = {"creator": creator, "characters": characters, "source": source}
            elif index_id == 41:
                # 41->twitter
                found_json['index'] = "twitter"
                url = results['results'][0]['data']['ext_urls'][0]
                date = results['results'][0]['data']['created_at']
                creator = results['results'][0]['data']['twitter_user_handle']
                found_json['data']={"url": url, "date": date, "creator": creator}
            elif index_id ==18:
                # 18-> H-Misc nhentai
                found_json['index'] = "H-Misc"
                source = results['results'][0]['data']['source']
                creator = results['results'][0]['data']['creator']
                if type(creator) == list:
                    creator = (lambda x: ", ".join(x))(creator)
                found_json['data'] = {"source": source, "creator": creator}
                if (x:=results['results'][0]['data']['jp_name']):
                    found_json['data']['jp_name']=x
                if (x:=results['results'][0]['data']['eng_name']):
                    found_json['data']['eng_name']=x

            elif index_id == 31:
                # 31 -> bcy.net
                found_json['index'] = "bcy"
                url = results['results'][0]['data']['ext_urls'][0]
                title = results['results'][0]['data']['title']
                member_name = results['results'][0]['data']['member_name']
                found_json['data']={'title': title,'url': url, 'member_name': member_name}

            elif index_id == 39:
                # 39 -> Artstation
                found_json['index'] = "artstation"
                url = results['results'][0]['data']['ext_urls'][0]
                title = results['results'][0]['data']['title']
                author_name = results['results'][0]['data']['author_name']
                found_json['data']={'title': title,'url': url, 'author_name': author_name}

            else:
                return Response(ACTION_FAILED, message=f"Unhandled Index {index_id},check log for more infomation")
            #found_json['index'] = index
            found_json['rate']=rate
            return Response(ACTION_SUCCESS, content=found_json)

        else:
            if int(results['header']['long_remaining']) < 1:  # could potentially be negative
                return Response(ACTION_FAILED, message="Out of searches today. ")

            if int(results['header']['short_remaining']) < 1:
                return Response(ACTION_FAILED, message="Out of searches in 30s. ")

    elif r.status_code == 403:
        return Response(ACTION_FAILED, message="Incorrect or Invalid API Key!")
    else:
        return Response(ACTION_FAILED, message=f"Error Code: {str(r.status_code)}")
