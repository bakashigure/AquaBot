# -*- coding:utf-8 -*-
"""
试图实现一些阿里云OSS的异步操作
"""

import oss2
#from config import _config
import hashlib
import asyncio
import aiofiles
import base64
import hmac
import httpx
from loguru import logger
from typing import Literal
from urllib.parse import urlparse
from email.utils import formatdate

from keys import _config, __url

prarms = dict()
prarms['access_key_id'] = _config['access_key_id']
prarms['access_key_secret'] = _config['access_key_secret']
prarms['endpoint'] = _config['endpoint']


class _Base():
    def __init__(self, auth, endpoint, is_cname, session,
                 connect_timeout,
                 app_name="",
                 enable_crc=True):
        self.auth = auth
        self.access_key_id = self.auth.access_key_id
        self.access_key_secret = self.auth.access_key_secret
        self.endpoint = endpoint
        self.session = session
        self.timeout = connect_timeout
        self.app_name = app_name
        self.enable_crc = enable_crc

        self.prarms = dict()

    def _make_signature(self, method, key):
        canonicalized_resource = '/' + self.bucket_name + '/' + key
        content_type = 'text/html'
        VERB = method
        date = formatdate(usegmt=True)
        to_sign = "{0}\n\n\n{1}\n{2}".format(VERB, date, canonicalized_resource)
        print("to_sign: %s"%to_sign)
        _sig = hmac.new(to_bytes(self.auth.access_key_secret), to_bytes(to_sign), hashlib.sha1)
        signature = b64encode_as_string(_sig.digest())
        Authorization = "OSS " + self.auth.access_key_id + ":" + signature
        logger.info("Authorization: %s"%Authorization)
        headers = dict()
        headers['authorization'] = Authorization
        headers['date'] = date
        headers['User-Agent'] = user_agent
        logger.info("headers: %s"%headers)
        return headers

    def _make_url(self, bucket_name: str, key=''):
        u = urlparse(self.endpoint)
        return u.scheme + '://' + bucket_name + '.' + u.netloc + '/' + key

    async def do(self, method, bucket_name, key, **kwargs):
        url = self._make_url(bucket_name, key)
        headers = self._make_signature(method=method, key=key)
        print("url: ", url)
        async with httpx.AsyncClient() as client:
            logger.info("kwargs: %s"%kwargs)
            req = Request(method,url,headers=headers,**kwargs)
            request = httpx.Request(req.method,req.url,data=req.data,headers=headers)
            print(request)
            r = await client.send(request)
            logger.info("status_code: %s" %r.status_code)
            logger.info("content: %s"%r.content) 
            return r


class Request():
    def __init__(self,method,url,
                 data=None,
                 params=None,
                 headers=None):
        self.method=method
        self.url=url
        self.data=_convert_request_body(data)
        self.params=params or {}


def _convert_request_body(data):
    data = to_bytes(data)

    if hasattr(data, '__len__'):
        return data

    return data


class Auth(_Base):
    def __init__(self, access_key_id: str, access_key_secret: str, auth_version: Literal['v1', 'v2'] = 'v1'):
        self.access_key_id = access_key_id.strip()
        self.access_key_secret = access_key_secret.strip()


class Bucket(_Base):
    def __init__(self, auth, endpoint, bucket_name,
                 is_cname=False,
                 session=None,
                 connect_timeout=None,
                 app_name=None,
                 enable_crc=True):
        self.bucket_name = bucket_name.strip()
        super(Bucket, self).__init__(auth, endpoint, is_cname, session, connect_timeout, app_name, enable_crc)

    async def get_object(self, key,
                         byte_range=None,
                         headers=None,
                         process_callback=None,
                         process=None,
                         params=None):
        return await self.do(method="GET", bucket_name=self.bucket_name, key=key)

    async def get_object_to_file(self, key, filename,
                                 byte_range=None,
                                 headers=None,
                                 process_callback=None,
                                 process=None,
                                 params=None):
        res = await self.get_object(key, byte_range=byte_range, headers=headers, process_callback=process_callback, process=process, params=params)

        async with aiofiles.open(filename, mode='wb') as f:
            await f.write(res.content)
        return res

    async def put_object(self, key, data,
                         headers=None,
                         progress_callback=None):
        return await self.do('PUT',self.bucket_name,key)


    async def put_object_from_file(self,key,filename,
                                   headers=None,
                                   progress_callback=None):
        async with aiofiles.open(filename, mode='rb') as f:
            return await self.put_object(key,f,headers,progress_callback=progress_callback)
   
    async def append_object(): ...
    async def list_objects(): ...
    async def list_objects_v2(): ...
    async def sign_url(): ...
    async def put_object_with_url(): ...
    async def put_object_with_url_from_file(): ...
    async def select_object(): ...


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"


def to_bytes(data):
    """若输入为str（即unicode），则转为utf-8编码的bytes；其他则原样返回"""
    if isinstance(data, str):
        return data.encode(encoding='utf-8')
    else:
        return data


def b64encode_as_string(data):
    return to_string(base64.b64encode(to_bytes(data)))


def to_string(data):
    """若输入为bytes，则认为是utf-8编码，并返回str"""
    if isinstance(data, bytes):
        return data.decode('utf-8')
    else:
        return data


async def main():
    auth = Auth(_config['access_key_id'], _config['access_key_secret'])
    bucket = Bucket(auth, _config['endpoint'], _config['bucket'])
    #await bucket.get_object_to_file(key='img/aqua/10.jpg', filename=r'G:\10.jpg')
    #await bucket.put_object_from_file(key='img/testt.jpg', filename=r'G:\10.jpg')
    await bucket.put_object(key='img/ss.txt',data="test")
def ossrun():
    auth=oss2.Auth(_config['access_key_id'], _config['access_key_secret'])
    bucket=oss2.Bucket(auth, _config['endpoint'], _config['bucket'])

    bucket.put_object_from_file(key='img/through_oss.jpg', filename=r'G:\10.jpg')
asyncio.run(main())

#ossrun()