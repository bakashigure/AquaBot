AquaBot 凑·阿库娅bot v2.2.2
=========================
此项目为基于nonebot2的bot，可以通过指令发夸图和上传夸图和其他的功能  
属于几乎纯自用bot，所以你很可能部署不起来  
凑·阿库娅(湊あくあ)(Minato aqua)是hololive二期生的虚拟YouTuber  
夸图指凑·阿库娅的同人图


Installation
=========================
[nonebot2](https://v2.nonebot.dev/)  
[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)  
前置技能要求: 阅读过nonebot与go-cqhttp的文档.

除此之外，您可能还需要一些的, 能访问pixiv和saucenao的方式.

.env 配置
=========================
```
ENVIRONMENT=dev
DEBUG=false
HOST=0.0.0.0
PORT=7777

COMMAND_START=["","/","."]
CQHTTP="" # cqhttp路径

AQUA_BOT_DEBUG=True #[true,false] bot调试, 用于aqua debug与 aqua func
AQUA_BOT_PIC_STORAGE=local #['local'] 存储模式, 目前只支持'local'
AQUA_BOT_DATABASE="" #数据库路径, 指定一个json文件

AQUA_BOT_PIC_DIR="" # 图片存储路径
AQUA_BOT_PIC_CACHE_DIR="" # 压缩图片过程中的缓存文件位置

# !注意 OSS部分没写完, 所以下面的OSS相关配置不需要填也不能填

AQUA_BOT_OSS_ACCESS_KEY_ID="" # oss access key id
AQUA_BOT_OSS_ACCESS_KEY_SECRET="" # oss access key secret
AQUA_BOT_OSS_BUCKET="" # oss bucket name
AQUA_BOT_OSS_ENDPOINT='' # oss endpoint
AQUA_BOT_OSS_PREFIX="" # oss prefix

AQUA_BOT_LANGUAGE="chinese" # ['chinese'] bot语言, 目前只支持中文
AQUA_BOT_PIXIV_REFRESH_TOKEN="" # pixiv refresh token, 访问pixiv所需
AQUA_BOT_SAUCENAO_API="" # saucenao api key, 用于搜图

```


Usage
=========================
```
* aqua random - 一张随机夸图, 或大喊'夸图来','来点夸图',或戳一戳bot
            - 回复这张图'id'来获得其id
* aqua more - 查看更多夸图, 或大喊'多来点夸图'
* aqua help - 您要找的是不是 'aqua help'?
* aqua upload [夸图] - 上传夸图(支持多张)
* aqua delete [夸图id] - 删除夸图
* aqua pixiv (可选关键词) ['day','week','month'] [index] - 返回关键词在指定区间内最受欢迎的第index张图
* aqua search [图] - 在saucenao和ascii2d中搜索这张图(支持多张), 支持来源twitter, pixiv...
* aqua stats - 现在有多少张夸图?
_____________________________________
* aqua debug [cmd] - 执行内部指令, 并输出结果(可能) 
* aqua func [cmd] - 执行内部异步函数, 并输出结果(可能) 
* aqua save - 保存当前夸图数据库到json 
* aqua reload - 重新读取夸图列表 
TIP: 请注意指令间的空格
```
ChangeLog
=========================
`2.3.0`
* [+] 支持连续对话, 重写部分逻辑

`2.2.2 - 2.2.3`
* [+] 修bug

`2.2.1`
* [+] 适配nb2 b1

`2.2.0`
* [+] ascii2d中添加了特征检索

`2.1.0`
* [+] 搜索来源中增加了ascii2d

`v2.0.4`
* [+] 修bug修bug
* [+] 重新添加了每日一夸

`v2.0.3`
* [+] 修改pixiv认证
* [+] 修复upload

`v2.0.2`
* [+] 修改上传, 支持多张图片/多个pid 一次性上传

`v2.0.1`
* [+] 修改部分pixiv逻辑


`v2.0.0` 
* 重构版本  
