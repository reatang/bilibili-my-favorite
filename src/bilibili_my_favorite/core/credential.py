import urllib.parse
import time
from bilibili_api import Credential
from bilibili_api.exceptions import ArgsException

class SuperCredential(Credential):
    """
    继承 Credential 类，重写 get_cookies 方法
    支持从原始 cookies 字符串自动解析并配置凭据
    """

    def __init__(self, raw_cookies: str, ac_time_value: str = None):
        """
        初始化 SuperCredential
        
        Args:
            raw_cookies (str): 原始 cookies 字符串，格式如 "key1=value1; key2=value2; ..."
        """
        if not raw_cookies:
            raise ArgsException("[SuperCredential] raw_cookies 提供一个有效的值。")
        
        # 初始化额外的 cookies 存储
        self.super_cookies = {}

        # 如果提供了原始 cookies，解析它们
        original_cookies = self._parse_raw_cookies(raw_cookies)

        # 调用父类初始化
        super().__init__(
            sessdata=original_cookies.get('sessdata'),
            bili_jct=original_cookies.get('bili_jct'),
            buvid3=original_cookies.get('buvid3'),
            buvid4=original_cookies.get('buvid4'),
            dedeuserid=original_cookies.get('dedeuserid'),
            ac_time_value=ac_time_value,
        )


    def _parse_raw_cookies(self, raw_cookies: str):
        """
        解析原始 cookies 字符串
        
        Args:
            raw_cookies (str): 原始 cookies 字符串
        """
        # 标准的 Credential 字段映射
        credential_fields = {
            'SESSDATA': 'sessdata',
            'bili_jct': 'bili_jct', 
            'buvid3': 'buvid3',
            'buvid4': 'buvid4',
            'DedeUserID': 'dedeuserid',
            'ac_time_value': 'ac_time_value'
        }
        
        # 解析 cookies 字符串
        cookies_dict = {}
        for cookie_pair in raw_cookies.split(';'):
            cookie_pair = cookie_pair.strip()
            if '=' in cookie_pair:
                key, value = cookie_pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                cookies_dict[key] = value
        
        # 设置标准 Credential 字段
        original_cookies = {}
        for cookie_key, attr_name in credential_fields.items():
            if cookie_key in cookies_dict:
                value = cookies_dict[cookie_key]
                # 对 SESSDATA 进行 URL 编码处理（如果需要）
                if cookie_key == 'SESSDATA' and value.find("%") == -1:
                    value = urllib.parse.quote(value)
                original_cookies[attr_name] = value
                # 从额外 cookies 中移除已处理的标准字段
                del cookies_dict[cookie_key]
        
        # 剩余的 cookies 存储到 super_cookies 中
        self.super_cookies = cookies_dict

        return original_cookies

    def get_cookies(self) -> dict:
        """
        获取完整的 cookies 字典，包括标准字段和额外字段
        
        Returns:
            dict: 完整的 cookies 字典
        """
        # 先获取父类的标准 cookies
        cookies = super().get_cookies()
        
        # 合并额外的 cookies
        cookies.update(self.super_cookies)
        
        return cookies
    
    @classmethod
    def from_raw_cookies(cls, raw_cookies: str, ac_time_value: str = None) -> "SuperCredential":
        """
        从原始 cookies 字符串创建 SuperCredential 实例
        
        Args:
            raw_cookies (str): 原始 cookies 字符串
            
        Returns:
            SuperCredential: 新的实例
        """
        return cls(raw_cookies=raw_cookies, ac_time_value=ac_time_value)
