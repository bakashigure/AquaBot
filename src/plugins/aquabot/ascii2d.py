# -*- coding:utf-8 -*-
# Modified from https://github.com/kitUIN/PicImageSearch/blob/main/PicImageSearch/ascii2d.py 
# Created by bakashigure
from typing import Coroutine
from bs4 import BeautifulSoup
from loguru import logger
from requests_toolbelt import MultipartEncoder
import httpx 
import aiofiles
import asyncio
from .response import *

class Ascii2DNorm:
    URL = 'https://ascii2d.net'

    def __init__(self, data):
        self.thumbnail = ""
        self.detail: str = data[3].small.string
        self.title = ""
        self.authors = ""
        self.url = ""
        self.marks = ""
        self._arrange(data)

    def _arrange(self, data):
        o_url = data[3].find('div', class_="detail-box gray-link").contents
        urls = self._geturls(o_url)
        self.thumbnail = self.URL + data[1].find('img')['src']
        self.url = urls['url']
        self.title = urls['title']
        self.authors = urls['authors']
        self.marks = urls['mark']

    @staticmethod
    def _geturls(data):
        all_urls = {
            'url': "",
            'title': "",
            'authors_urls': "",
            'authors': "",
            'mark': ""
        }

        for x in data:
            if x == '\n':
                continue
            try:
                origin = x.find_all('a')
                all_urls['url'] = origin[0]['href']
                all_urls['title'] = origin[0].string
                all_urls['authors_urls'] = origin[1]['href']
                all_urls['authors'] = origin[1].string
                all_urls['mark'] = x.small.string
            except:
                pass
        return all_urls

    def __repr__(self):
        return f'<NormAscii2D(title={repr(self.title)}, authors={self.authors}, mark={self.marks})>'


class Ascii2DResponse:

    def __init__(self, resp):
        self.origin: list = resp
        self.raw: list = list()

        for ele in self.origin:
            detail = ele.contents
            self.raw.append(Ascii2DNorm(detail))

    def __repr__(self):
        return f'<Ascii2DResponse(count={repr(len(self.origin))}>'

class Ascii2D:
    """
    Ascii2D
    -----------
    Reverse image from https://ascii2d.net\n
    Params Keys
    -----------
    :param **requests_kwargs: proxy settings
    """

    def __init__(self, **requests_kwargs):
        self.requests_kwargs = requests_kwargs

    @staticmethod
    def _slice(res):
        soup = BeautifulSoup(res, 'html.parser')
        resp = soup.find_all(class_='row item-box')
        return Ascii2DResponse(resp)

    @staticmethod
    def _errors(code):
        if code == 404:
            return "Source down"
        elif code == 302:
            return "Moved temporarily, or blocked by captcha"
        elif code == 413 or code == 430:
            return "image too large"
        elif code == 400:
            return "Did you have upload the image ?, or wrong request syntax"
        elif code == 403:
            return "Forbidden,or token unvalid"
        elif code == 429:
            return "Too many request"
        elif code == 500 or code == 503:
            return "Server error, or wrong picture format"
        else:
            return f"Unknown error{code}"

    async def search(self, url):
        """
        Ascii2D
        -----------
        Reverse image from https://ascii2d.net\n
        Return Attributes
        -----------
        • .origin = Raw data from scrapper\n
        • .raw = Simplified data from scrapper\n
        • .raw[0] = First index of simplified data that was found\n
        • .raw[0].title = First index of title that was found\n
        • .raw[0].url = First index of url source that was found\n
        • .raw[0].authors = First index of authors that was found\n
        • .raw[0].thumbnail = First index of url image that was found\n
        • .raw[0].detail = First index of details image that was found
        """

        files = {'file': ("img.png", open(url, 'rb'),"image/png")}
        client = httpx.AsyncClient(proxies="http://127.0.0.1:7890",follow_redirects=True)
        try:
            color_res = await client.post("https://ascii2d.net/search/multi", files=files)
        except httpx.ReadTimeout:
            await client.aclose()
            return BaseResponse(ACTION_FAILED,"timeout")
        except httpx.ProxyError:
            await client.aclose()
            return BaseResponse(ACTION_FAILED,"proxy error")
        bovw_url = color_res.url.__str__().replace("/color/","/bovw/")
        bovw_res = await client.get(bovw_url,follow_redirects=True)
        await client.aclose() 
        #res = requests.post(ASCII2DURL, headers=headers, data=m, verify=False, **self.requests_kwargs)
       
        if color_res.status_code == 200 and bovw_res.status_code==200:
            # 处理逻辑： 先看第一个返回结果是否带上title，如果有说明这张图已经被搜索过了，有直接结果
            # 如果第一个结果的title为空，那么直接返回第二个结果，带上缩略图让用户自行比对是否一致
            _color_res =  self._slice(color_res.text)
            _bovw_res = self._slice(bovw_res.text)
            if _color_res.raw[0].title != "":
            #    return BaseResponse(ACTION_FAILED,"ascii2d not found.")
                return BaseResponse(ACTION_SUCCESS, "get direct result from ascii2d color",{'index':"ascii2d", 'url': _color_res.raw[0].url, 'authors': _color_res.raw[0].authors})
            else:
                if _bovw_res.raw[0].title!="":
                    return BaseResponse(ACTION_SUCCESS, "get direct result from ascii2d bovw",{'index':"ascii2d", 'url': _bovw_res.raw[0].url, 'authors': _bovw_res.raw[0].authors})

                return BaseResponse(ACTION_WARNING, "get possible result from ascii2d",[
                    {'index':"ascii2d颜色检索",  'url': _color_res.raw[1].url, 'authors': _color_res.raw[1].authors},_color_res.raw[1].thumbnail,
                    {'index':"ascii2d特征检索",  'url': _bovw_res.raw[1].url, 'authors': _bovw_res.raw[1].authors},_bovw_res.raw[1].thumbnail])    
        else:
            return BaseResponse(ACTION_FAILED, self._errors(color_res.status_code))

        #except Exception as e:
        #    logger.error(e)


