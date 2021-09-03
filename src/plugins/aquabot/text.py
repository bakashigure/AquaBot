class TEXT:
    text = dict()
    text['english'] = dict()
    text['chinese'] = dict()

    # English config
    text['english']['error_cqhttp_path_not_exist'] = ""
    text['english']['error_path_not_exist'] = ""
    text['english']['warning_local_storage_path_not_exist'] = ""
    text['english']['error_oss_path_not_exist']=""
    text['english']['warning_oss_test']=""
    text['english']['success_oss_test']=""
    text['english']['error_oss_test_permission']=""
    text['english']['error_oss_text']=""
    text['english']['error_storage_method']=""
    text['english']['warning_pixiv_token_not_set']=""
    text['english']['warning_saucenao_api_not_set']=""
    text['english']['warning_language_not_exist']=""


    # Chinese config
    text['chinese']['error_cqhttp_path_not_exist'] = "未设置cqhttp路径, 请修改.env文件"
    text['chinese']['error_path_not_exist'] = "本地存储路径%s不存在, 请手动创建或修改.env文件"
    text['chinese']['warning_local_storage_path_not_exist'] = "本地存储路径未配置, 默认存放于bot根目录下src/plugins/aquabot/img目录"
    text['chinese']['error_oss_path_not_exist'] = "您选择了%s的存储方式,但 aqua_bot_oss_%s 未设置, 请检查.env文件, 配置详见%s"
    text['chinese']['warning_oss_test'] = "检测oss连通性..."
    text['chinese']['success_oss_test'] = "oss连通性测试成功"
    text['chinese']['error_oss_test_permission']="连接oss时发生权限错误, 请检查access_key_id和access_key_secret是否正确"
    text['chinese']['error_oss_test'] = "连接oss时发生其他错误, 详见oss配置文档 https://help.aliyun.com/document_detail/32039.html"
    text['chinese']['error_storage_method']="存储方式不正确, 请检查.env文件, 配置详见%s"
    text['chinese']['warning_pixiv_token_not_set']="没有设置pixiv refresh token, pixiv相关功能将不可使用"
    text['chinese']['warning_saucenao_api_not_set']="没有设置saucenao api, 搜图相关功能将不可使用"
    text['chinese']['warning_language_not_exist']="语言设置不正确, 请检查.env文件"