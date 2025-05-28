from typing import Union

from bilibili_api.exceptions import ArgsException
from bilibili_api.utils.network import Api
from bilibili_api import Credential


async def get_download_url(
    cid: int,
    bvid: str,
    credential: Credential,
    *,
    qn: int = 112,
) -> dict:
    """
    获取视频下载链接
    重构了源视频url读取接口

    """
    api = {
        "url": "https://api.bilibili.com/x/player/playurl",
        "method": "GET",
        "verify": False,
        "params": {
            "bvid": "int: bv 号",
            "cid": "int: 分 P 编号",
            "qn": "int: 视频质量编号，最高 112",
            "otype": "const str: json",
            "fnval": "const int: 4048",
            "platform": "int: 平台"
        },
        "comment": "视频下载的信息，下载链接需要提供 headers 伪装浏览器请求（Referer 和 User-Agent）"
    }
    
    
    params = {
        "bvid": bvid,
        "cid": cid,
        "qn": qn,
        "fnver": 0,
        "fnval": 16,
        "fourk": 1,
    }
    return (
        await Api(**api, credential=credential, wbi=True)
        .update_params(**params)
        .result
    )
