# -*- coding:utf-8 -*-

import io
import json
import re
from collections import OrderedDict

import httpx
from PIL import Image, ImageFile

from .response import *

# Modified from https://saucenao.com/tools/examples/api/identify_images_v1.1.py
# Created by bakashigure
# Last updated 2021/5/18


Response = BaseResponse


async def saucenao_search(file_path: str, APIKEY: str, proxies=None)->Response:
    """saucenao search moudle

    Args:
    >>> file_path: target picture
    >>> APIKEY: saucenao APIKEY (apply from https://saucenao.com/account/register)
    >>> proxies: proxy server (default: None)

    Returns:
    >>> Response: Response
    """
    bitmask_all = '999'
    default_minsim = '80!'
    _message = {}
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    image = Image.open(file_path)
    image = image.convert('RGB')
    thumbSize = (250, 250)
    image.thumbnail(thumbSize, resample=Image.ANTIALIAS)
    imageData = io.BytesIO()
    image.save(imageData, format='PNG')

    url_all = 'http://saucenao.com/search.php?output_type=2&numres=1&minsim=' + default_minsim + '&db=' + \
        bitmask_all + '&api_key=' + APIKEY
    files = {'file': (file_path, imageData.getvalue())}
    imageData.close()
    # proxy={"https":"http://127.0.0.1:7890"}
    async with httpx.AsyncClient(proxies=proxies) as client:
        r = await client.post(url=url_all, files=files, timeout=6)
        if r.status_code != 200:
            if r.status_code == 403:
                return Response(ACTION_FAILED, message="Incorrect or Invalid API Key!")
            else:
                return Response(ACTION_FAILED, message="Error Code: " + str(r.status_code))
        else:
            results = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
            if int(results['header']['user_id']) > 0:
                # api responded
                print('Remaining Searches 30s|24h: ' + str(
                    results['header']['short_remaining']) + '|' + str(results['header']['long_remaining']))
                if int(results['header']['status']) == 0:
                    # search succeeded for all indexes, results usable
                    ...
                else:
                    if int(results['header']['status']) > 0:
                        # One or more indexes are having an issue.
                        # This search is considered partially successful, even if all indexes failed, so is still counted against your limit.
                        # The error may be transient, but because we don't want to waste searches, allow time for recovery.
                        return Response(ACTION_FAILED, "API Error. ")
                    else:
                        # Problem with search as submitted, bad image, or impossible request.
                        # Issue is unclear, so don't flood requests.
                        return Response(ACTION_FAILED, "Bad image or other request error. ")
            else:
                # General issue, api did not respond. Normal site took over for this error state.
                # Issue is unclear, so don't flood requests.
                return Response(ACTION_FAILED, "Bad image or API failure. ")

        # print(results)
        found_json = {"type": "success", "rate": "{0}%".format(str(results['results'][0]['header']['similarity'])), "data": {}}

        if int(results['header']['results_returned']) > 0:
            artwork_url = ""
            print(results)
            rate = results['results'][0]['header']['similarity']+'%'
            # one or more results were returned
            if float(results['results'][0]['header']['similarity']) > float(results['header']['minimum_similarity']):
                print('hit! ' + str(results['results']
                                    [0]['header']['similarity']))
                # print(results)
                # get vars to use
                service_name = ''
                illust_id = 0
                member_id = -1
                index_id = results['results'][0]['header']['index_id']
                page_string = ''
                page_match = re.search(
                    '(_p[\d]+)\.', results['results'][0]['header']['thumbnail'])
                if page_match:
                    page_string = page_match.group(1)

                if index_id == 5 or index_id == 6:
                    # 5->pixiv 6->pixiv historical
                    service_name = 'pixiv'
                    member_name = results['results'][0]['data']['member_name']
                    illust_id = results['results'][0]['data']['pixiv_id']
                    title = results['results'][0]['data']['title']
                    found_json['index'] = "pixiv"
                    found_json['data']['pixiv'] = {"title": title, "illust_id": illust_id, "member_name": member_name}
                    artwork_url = "https://pixiv.net/artworks/{}".format(
                        illust_id)
                elif index_id == 8:
                    # 8->nico nico seiga
                    service_name = 'seiga'
                    member_id = results['results'][0]['data']['member_id']
                    illust_id = results['results'][0]['data']['seiga_id']
                    found_json['data']['seiga'] = {"member_id": member_id, "illust_id": illust_id}
                elif index_id == 10:
                    # 10->drawr
                    service_name = 'drawr'
                    member_id = results['results'][0]['data']['member_id']
                    illust_id = results['results'][0]['data']['drawr_id']
                    found_json['data']['drawr'] = {"member_id": member_id, "illust_id": illust_id}
                elif index_id == 11:
                    # 11->nijie
                    service_name = 'nijie'
                    member_id = results['results'][0]['data']['member_id']
                    illust_id = results['results'][0]['data']['nijie_id']
                    found_json['data']['nijie'] = {"member_id": member_id, "illust_id": illust_id}
                elif index_id == 34:
                    # 34->da
                    service_name = 'da'
                    illust_id = results['results'][0]['data']['da_id']
                    found_json['data']['da'] = {"illust_id": illust_id}
                elif index_id == 9:
                    # 9 -> danbooru
                    # index name, danbooru_id, gelbooru_id, creator, material, characters, sources
                    found_json['index'] = "danbooru"
                    creator = results['results'][0]['data']['creator']
                    characters = results['results'][0]['data']['characters']
                    source = results['results'][0]['data']['source']
                    found_json['data']['danbooru'] = {"creator": creator, "characters": characters, "source": source}
                elif index_id == 38:
                    # 38 -> H-Misc (E-Hentai)
                    found_json['index'] = "H-Misc"
                    source = results['results'][0]['data']['source']
                    creator = results['results'][0]['data']['creator']
                    if type(creator) == list:
                        creator = (lambda x: ", ".join(x))(creator)
                    jp_name = results['results'][0]['data']['jp_name']
                    found_json['data']['H-Misc'] = {"source": source, "creator": creator, "jp_name": jp_name}
                elif index_id == 12:
                    # 12 -> Yande.re
                    # ext_urls, yandere_id, creator, material, characters, source
                    found_json['index'] = "yandere"
                    creator = results['results'][0]['data']['creator']
                    if type(creator) == list:
                        creator = (lambda x: ", ".join(x))(creator)
                    characters = results['results'][0]['data']['characters']
                    source = results['results'][0]['data']['source']
                    found_json['data']['yandere'] = {"creator": creator, "characters": characters, "source": source}

                else:
                    # unknown
                    return Response(ACTION_FAILED, message=f"Unhandled Index {index_id},check log for more infomation")

                return Response(ACTION_SUCCESS, content=found_json)

            else:
                _s = f"rate: {rate}\nnot found... ;_;"
                return Response(ACTION_WARNING, message=_s)


        else:
            if int(results['header']['long_remaining']) < 1:  # could potentially be negative
                return Response(ACTION_FAILED, message="Out of searches today. ")

            if int(results['header']['short_remaining']) < 1:
                return Response(ACTION_FAILED, message="Out of searches in 30s. ")
