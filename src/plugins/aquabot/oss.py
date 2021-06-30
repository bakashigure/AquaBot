# -*- coding:utf-8 -*-
"""
试图实现一些阿里云OSS的异步操作
"""

import oss2
#from config import _config
import hashlib
import asyncio
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
        self.timeout=connect_timeout
        self.app_name = app_name
        self.enable_crc = enable_crc

        self.prarms=dict()

    def _make_signature(self,method,key):
        canonicalized_resource = '/'+self.bucket_name+'/'+key
        content_type = 'text/html'
        _VERB = 'GET'
        _date = formatdate(usegmt=True)
        to_sign = "{0}\n\n\n{1}\n{2}".format(_VERB, _date, canonicalized_resource)
        print("TO_SIGN:\n\n %s\n\n" % to_sign)
        _sig = hmac.new(to_bytes(self.auth.access_key_secret), to_bytes(to_sign), hashlib.sha1)
        signature = b64encode_as_string(_sig.digest())
        Authorization = "OSS " + self.auth.access_key_id + ":" + signature
        print("Authorization: ", Authorization)
        headers = dict()
        headers['Authorization'] = Authorization
        headers['date'] = _date
        headers['User-Agent'] = user_agent
        print(headers)
        return headers

    def _make_url(self,bucket_name:str,key=''):
        u=urlparse(self.endpoint)
        return u.scheme+'://'+bucket_name+'.'+u.netloc+'/'+key


    async def do(self,method,bucket_name,key='',**kwargs):
        url= self._make_url(bucket_name,key)
        headers=self._make_signature(method=method,key=key)
        print("url: ",url)
        async with httpx.AsyncClient() as client:
            request=httpx.Request(method,url,**kwargs,headers=headers)
            r= await client.send(request)
            print(r)
            print(r.content)


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
        super(Bucket, self).__init__(auth,endpoint,is_cname,session,connect_timeout,app_name,enable_crc)


    async def get_object(self,key,
                   byte_range=None,
                   headers=None,
                   process_callback=None,
                   process=None,
                   params=None):
        return await self.do(method="GET",bucket_name=self.bucket_name,key=key)


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"


def make_signature():
    _sign = "OSS2 AccessKeyID:{0},Signature:{1}".format(prarms['access_key_id'])

    date = formatdate(usegmt=True)


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
    bucket = Bucket(auth, _config['endpoint'],_config['bucket'])
    await bucket.get_object('img/aqua/10.jpg')


asyncio.run(main())