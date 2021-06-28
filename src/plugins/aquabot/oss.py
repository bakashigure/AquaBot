# -*- coding:utf-8 -*-
"""
试图实现一些阿里云OSS的异步操作
"""

import oss2
#from config import _config
import hashlib
import base64
import hmac
import httpx
from email.utils import formatdate

from .keys import _config,__url

prarms=dict()
prarms['access_key_id']=_config['access_key_id']
prarms['access_key_secret']=_config['access_key_secret']


user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

def make_signature():
    _sign="OSS2 AccessKeyID:{0},Signature:{1}".format(prarms['access_key_id'])

    date=formatdate(usegmt=True)

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


def put_object(key=None,data=None,headers=None):
    _host='https://oss-cn-hangzhou.aliyuncs.com'
    #_host=_config['bucket']+'.'+_config['endpoint'][8:]
    canonicalized_resource='/bakaimg/img/aqua/16544.jpg'
    content_type='text/html'
    _VERB='GET'
    _date=formatdate(usegmt=True)
    to_sign="{0}\n\n\n{1}\n{2}".format(_VERB, _date,canonicalized_resource)
    print("TO_SIGN:\n\n %s\n\n"%to_sign)
    _sig=hmac.new(to_bytes(_config['access_key_secret']),to_bytes(to_sign),hashlib.sha1)
    
    print("_sig: %s"%_sig)
  

    #Signature = base64.b64encode(_sig.digest())
    signature = b64encode_as_string(_sig.digest())
    Authorization = "OSS "+_config['access_key_id'] +":"+signature
    print("Authorization: ",Authorization)
    headers=dict()
    headers['Authorization']= Authorization
    headers['date']=_date
    headers['User-Agent']= user_agent



    r=httpx.request(method='GET',url=__url,headers=headers)
    print(r)
    return r



def ossau():
    auth=oss2.Auth(_config['access_key_id'],_config['access_key_secret'])
    bucket=oss2.Bucket(auth,'https://oss-cn-hangzhou.aliyuncs.com','bakaimg')
    bucket.get_object('img/aqua/10.jpg')



#ossau()
r=put_object()
print(r.content)