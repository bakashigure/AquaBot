# -*- coding:utf-8 -*-
"""
试图实现一些阿里云OSS的异步操作
"""

import re
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

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

_subresource_key_set = frozenset(
    ['response-content-type', 'response-content-language',
        'response-cache-control', 'logging', 'response-content-encoding',
        'acl', 'uploadId', 'uploads', 'partNumber', 'group', 'link',
        'delete', 'website', 'location', 'objectInfo', 'objectMeta',
        'response-expires', 'response-content-disposition', 'cors', 'lifecycle',
        'restore', 'qos', 'referer', 'stat', 'bucketInfo', 'append', 'position', 'security-token',
        'live', 'comp', 'status', 'vod', 'startTime', 'endTime', 'x-oss-process',
        'symlink', 'callback', 'callback-var', 'tagging', 'encryption', 'versions',
        'versioning', 'versionId', 'policy', 'requestPayment', 'x-oss-traffic-limit', 'qosInfo', 'asyncFetch',
        'x-oss-request-payer', 'sequential', 'inventory', 'inventoryId', 'continuation-token', 'callback',
        'callback-var', 'worm', 'wormId', 'wormExtend', 'replication', 'replicationLocation',
        'replicationProgress']
)


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

        self.prarms = {}

    def _make_signature(self, method, bucket, date, key) -> str:
        canonicalized_resource = f'/{bucket}/{key}' if bucket else f'/{key}'
        content_type = 'text/html'
        VERB = method
        to_sign = "{0}\n\n\n{1}\n{2}".format(VERB, date, canonicalized_resource)
        print(f"to_sign: {to_sign}")
        _sig = hmac.new(to_bytes(self.auth.access_key_secret), to_bytes(to_sign), hashlib.sha1)
        signature = b64encode_as_string(_sig.digest())
        Authorization = f"OSS {self.auth.access_key_id}:{signature}"
        logger.info(f"Authorization: {Authorization}")

        return Authorization

    def _make_headers(self, authorization, date):
        _headers = {
            'authorization': authorization,
            'date': date,
            'User-Agent': user_agent,
        }

        logger.info(f"headers: {_headers}")
        '''
        for k, v in kwargs.items():
            _headers[k.lower()] = v
        '''
        return _headers

    def _make_url(self, bucket_name: str, key=''):
        u = urlparse(self.endpoint)
        return f'{u.scheme}://{bucket_name}.{u.netloc}/{key}'

    async def do(self, method, bucket_name, key, **kwargs):
        url = self._make_url(bucket_name, key)
        req = Request(method, url, **kwargs)

        authorization = self._make_signature(method, self.bucket_name, req.date, req.canonicalized_resource)
        headers = self._make_headers(authorization, req.date)

        async with httpx.AsyncClient() as client:
            logger.info(f"kwargs: {kwargs}")
            request = httpx.Request(req.method, req.url, data=req.data, headers=headers)
            print(request)
            r = await client.send(request)
            logger.info(f"status_code: {r.status_code}")
            logger.info(f"content: {r.content}")
            return r


class Request():
    def __init__(self, method, url,
                 data=None,
                 params=None,
                 headers=None):
        self.method = method
        self.url = url
        self.data = _convert_request_body(data)
        self.params = params or {}
        self.date = self._make_date()
        self.canonicalized_resource = ''
        self.headers = params
        print('params', params)

        sub_params = {}
        if params:
            for k, v in params.items():
                if (_k := k.lower()) in _subresource_key_set:
                    sub_params[_k] = v

            print('sub_params',sub_params)

        sorted(sub_params.items(),key=lambda x:x[0])
        if sub_params:
            self.canonicalized_resource = '?' + '&'.join(self.__param_to_query(k, v) for k, v in sub_params.items())

    def _make_date(self) -> str:
        return formatdate(usegmt=True)

    def __param_to_query(self, k, v):
        return f'{k}={v}' if v else k


def _convert_request_body(data):
    data = to_bytes(data)

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
        return await self.do('PUT', self.bucket_name, key)

    async def put_object_from_file(self, key, filename,
                                   headers=None,
                                   progress_callback=None):
        async with aiofiles.open(filename, mode='rb') as f:
            return await self.put_object(key, f, headers, progress_callback=progress_callback)

    async def list_objects(self, prefix='',
                           delimiter='',
                           marker='',
                           max_keys=100,
                           headers=None):
        return await self.do('GET', self.bucket_name, '',
                             params={'prefix': prefix,
                                     'delimiter': delimiter,
                                     'marker': marker,
                                     'max_keys': max_keys,
                                     'encoding-type': 'url'},
                             headers=headers)

    async def list_objects_v2(self, prefix='',
                              delimiter='',
                              continuation_token='',
                              start_after='',
                              fetch_owner=False,
                              encoding_type='url',
                              max_keys=100
                              ):
        return await self.do(
            'GET',
            self.bucket_name,
            '',
            params={
                'list-type': '2',
                'prefix': prefix,
                'delimiter': delimiter,
                'continuation-token': continuation_token,
                'start-after': start_after,
                'fetch-owner': str(fetch_owner).lower(),
                'max-keys': str(max_keys),
                'encoding-type': encoding_type,
            },
        )

    '''
    async def append_object(): ...
    async def sign_url(): ...
    async def put_object_with_url(): ...
    async def put_object_with_url_from_file(): ...
    async def select_object(): ...
    '''


class _BaseIterator():
    def __init__(self, marker, max_retries):
        self.is_truncated = True
        self.next_marker = marker

        max_retries = 3 if max_retries is None else max_retries
        self.max_retries = max_retries if max_retries > 0 else 1
        self.entries = []

    def _fetch(self):
        raise NotImplemented

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if self.entries:
                return self.entries.pop(0)

            if not self.is_truncated:
                raise StopIteration

            self.fetch_with_retry()

    def next(self):
        return self.__next__()

    def fetch_with_retry(self):
        for _ in range(self.max_retries):
            try:
                self.is_truncated, self.next_marker = self._fetch()
            except Exception as e:
                if e.status // 100 != 5:
                    raise
            else:
                return


class ObjectIteratorV2(_BaseIterator):
    def __init__(self, bucket_name, prefix='', delimiter='',
                 continuation_token='',
                 start_after='',
                 fetch_owner=False,
                 encoding_type='url',
                 max_keys=100,
                 max_retries=None,
                 headers=None):
        super(ObjectIteratorV2, self).__init__(continuation_token, max_retries)
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.delimiter = delimiter
        self.start_after = start_after
        self.fetch_owner = fetch_owner
        self.encoding_type = encoding_type
        self.max_keys = max_keys
        self.headers = headers

    def _fetch(self):
        res = self.bucket.list_objects_v2(prefix=self.prefix,
                                          delimiter=self.delimiter,
                                          continuation_token=self.next_marker,
                                          start_after=self.start_after,
                                          fetch_owner=self.fetch_owner,
                                          encoding_type=self.encoding_type,
                                          max_keys=self.max_keys,
                                          headers=self.headers)

        self.entries = res.object_list + [SimplifiedObjectInfo(prefix, None, None, None, None, None)
                                          for prefix in res.prefix_list]

        self.entries.sort(key=lambda obj: obj.key)
        return res.is_truncated, res.next_continuation_token


class SimplifiedObjectInfo():
    def __init__(self, key, last_modified, etag, type, size, storage_class, owner=None):
        self.key = key
        self.last_modified = last_modified
        self.etag = etag
        self.type = type
        self.size = size
        self.storage_class = storage_class
        self.owner = owner

    def is_prefix(self):
        return self.last_modified is None


def to_bytes(data):
    """若输入为str（即unicode），则转为utf-8编码的bytes；其他则原样返回"""
    return data.encode(encoding='utf-8') if isinstance(data, str) else data


def b64encode_as_string(data):
    return to_string(base64.b64encode(to_bytes(data)))


def to_string(data):
    """若输入为bytes，则认为是utf-8编码，并返回str"""
    return data.decode('utf-8') if isinstance(data, bytes) else data


async def main():
    auth = Auth(_config['access_key_id'], _config['access_key_secret'])
    bucket = Bucket(auth, _config['endpoint'], _config['bucket'])
    # await bucket.get_object_to_file(key='img/aqua/10.jpg', filename=r'G:\10.jpg')
    # await bucket.put_object_from_file(key='img/testt.jpg', filename=r'G:\10.jpg')
    # await bucket.put_object(key='img/ss.txt', data="test")
    #res = await bucket.list_objects_v2('img/aqua')
    res = await bucket.get_object('img/aqua/10.jpg')
    print(res)

def ossrun():
    auth = oss2.Auth(_config['access_key_id'], _config['access_key_secret'])
    bucket = oss2.Bucket(auth, _config['endpoint'], _config['bucket'])

    #bucket.put_object_from_file(key='img/through_oss.jpg', filename=r'G:\10.jpg')
    #res = bucket.list_objects_v2('img/aqua')
    res = bucket.get_object('img/aqua/10.jpg',process='image/auto-orient,1/quality,q_100/format,jpg')
    print('res: ', res)
    #print('res.next_continuation_token: ', res.next_continuation_token)
    #print('res.object_list: ', res.object_list)
    #print('res.is_truncated', res.is_truncated)
    print('res.headers: ', res.headers)

#asyncio.run(main())
ossrun()
