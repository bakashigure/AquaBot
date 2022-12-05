__version__ = "2.6.1"

text = {"english": {}, "chinese": {}}
# English config
text["english"]["error_cqhttp_path_not_exist"] = ""
text["english"]["error_path_not_exist"] = ""
text["english"]["warning_local_storage_path_not_exist"] = ""
text["english"]["error_oss_path_not_exist"] = ""
text["english"]["warning_oss_test"] = ""
text["english"]["success_oss_test"] = ""
text["english"]["error_oss_test_permission"] = ""
text["english"]["error_oss_text"] = ""
text["english"]["error_storage_method"] = ""
text["english"]["warning_pixiv_token_not_set"] = ""
text["english"]["warning_saucenao_api_not_set"] = ""
text["english"]["warning_language_not_exist"] = ""


# Chinese config
text["chinese"]["error_cqhttp_path_not_exist"] = "未设置cqhttp路径, 请修改.env文件"
text["chinese"]["error_path_not_exist"] = "本地存储路径%s不存在, 请手动创建或修改.env文件"
text["chinese"]["warning_local_storage_path_not_exist"] = "本地存储路径未配置, 默认存放于bot根目录下src/plugins/aquabot/img目录"
text["chinese"]["error_oss_path_not_exist"] = "您选择了%s的存储方式,但 aqua_bot_oss_%s 未设置, 请检查.env文件, 配置详见%s"
text["chinese"]["warning_oss_test"] = "检测oss连通性..."
text["chinese"]["success_oss_test"] = "oss连通性测试成功"
text["chinese"]["error_oss_test_permission"] = "连接oss时发生权限错误, 请检查access_key_id和access_key_secret是否正确"
text["chinese"]["error_oss_test"] = "连接oss时发生其他错误, 详见oss配置文档 https://help.aliyun.com/document_detail/32039.html"
text["chinese"]["error_storage_method"] = "存储方式不正确, 请检查.env文件, 配置详见%s"
text["chinese"]["warning_pixiv_token_not_set"] = "没有设置pixiv refresh token, pixiv相关功能将不可使用"
text["chinese"]["warning_saucenao_api_not_set"] = "没有设置saucenao api, 搜图相关功能将不可使用"
text["chinese"]["warning_language_not_exist"] = "语言设置不正确, 请检查.env文件"

text["chinese"][
    "help"
] = f"""AquaBot v{__version__}
aqua random - 一张随机夸图, 或大喊'夸图来','来点夸图',或戳一戳bot\n\
            - 回复这张图'id'来获得其id\n\
aqua more - 查看更多夸图, 或大喊'多来点夸图'\n\
aqua help - 您要找的是不是 'aqua help'?\n\
aqua upload [夸图] - 上传夸图(支持多张)\n\
aqua delete [夸图id] - 删除夸图\n\
aqua pixiv (关键词) ['day','week','month'] [index] ('full') - 返回关键词在指定区间内最受欢迎的第index张图, 关键词中的空格请用下划线替代\n\
aqua search [图] - 在saucenao和ascii2d中搜索这张图(支持多张), 支持来源twitter, pixiv...\n\
aqua stats - 现在有多少张夸图?\n\
aqua chat [句子] - 与 chatgpt 聊天\n\
_____________________________________\n\
aqua debug [cmd] - 执行内部同步命令, 并输出结果(可能) \n\
aqua func [cmd] - 执行内部异步函数, 并输出结果(可能) \n\
aqua save - 保存当前夸图数据库到json \n\
aqua reload - 重新读取夸图列表 \n\
TIP: 请注意指令间的空格
"""

text["chinese"][
    "help_simple"
] = f"""AquaBot v{__version__}
aqua random [数量] - 随机夸图\n\
aqua more - 更多的夸图\n\
aqua help - 使用 'aqua help `keyword`' 查看命令详细帮助\n\
aqua upload [夸图] - 传图\n\
aqua delete [夸图id] - 删图\n\
aqua pixiv (可选关键词) [区间] [序号] ('full') - 爬图\n\
aqua illust [pid] (可选尺寸)\n\
aqua search [图] - 搜图\n\
aqua stats - 现在有多少张夸图?\n\
aqua chat [句子] - 与 chatgpt 聊天\n\
————————\n\
提供`keyword`以查看命令详细帮助
"""

text["chinese"][
    "help_random"
] = f"""aqua random [数量]\n\
随机夸图\n\
数量(可选): 最多5张, 置空为1\n\
或大喊'夸图来','来点夸图', 或戳一戳bot\n\
回复bot发送的图片`id`可获取此图id"""

text["chinese"][
    "help_more"
] = f"""aqua more\n\
随机2~4张夸图, 或大喊 '多来点夸图','来多点夸图'\n\
"""

text["chinese"][
    "help_help"
] = f"""aqua help [keyword]\n\
基本帮助\n\
keyword: ['random','more'...] 查看命令详细帮助"""

text["chinese"][
    "help_upload"
] = f"""aqua upload [夸图|PID]\n\
传夸图\n\
[夸图|PID]: 可以为图片, 也可以为pid, 支持同传多张, 但不能混传.
"""

text["chinese"][
    "help_delete"
] = f"""aqua delete [图片id]\n\
删除一张图\n\
图片id: 可通过回复bot`id`来获得.
"""

text["chinese"][
    "help_pixiv"
] = f"""aqua pixiv (可选关键词) [区间] [序号] (原图)\n\
pixiv搜图功能\n\
关键词(可选): 搜图关键词, 置空则默认为 '湊あくあ', 请尽量提供日语tag\n\
区间: 图的日期区间, 为['day','week','month']中的一个\n\
序号: 按热门排序后第几热门的图, 为一个数字\n\
原图(可选): 是否发送原图, 较大, 会慢\n\
    示例:
    aqua pixiv day 1 -> 当日最热门的夸图
    aqua pixiv 天宮こころ month 1 full -> 当月最热门的阿喵喵原图
"""

text["chinese"][
    "help_illust"
] = f"""aqua illust [pid] (可选尺寸)\n\
获取pid对应illust\n\
尺寸: 可选尺寸, 可选值为'large','medium','original', 默认为'large'\n\
"""

text["chinese"][
    "help_search"
] = f"""aqua pixiv search [图]\n\
搜图, 先找 saucenao, 没有最优解则返回 ascii2d 结果.\n\
图: 图, 支持多张同搜\n\
回复任意消息`搜`且删除消息中可能出现的@, 这样也能触发搜图.
"""

text['chinese']['help_stats'] = f'''aqua stats\n\
目前的夸图统计
'''

