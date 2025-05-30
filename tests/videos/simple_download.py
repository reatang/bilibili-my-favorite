import asyncio
from typing import Union
import urllib.parse

from bilibili_api.exceptions import ArgsException
from bilibili_api.utils.network import Api
from bilibili_api import video, Credential, get_client
import os
from dotenv import load_dotenv
from rich import print

from bilibili_my_favorite.core.credential import SuperCredential
from bilibili_my_favorite.utils.downloader import video_downloader
from bilibili_my_favorite.core.config import config

load_dotenv()

# https://api.bilibili.com/x/player/playurl?bvid=BV1NuJtzSEFt&cid=30053565341&qn=112&fiurk=1&fnval=16

# FFMPEG 路径，查看：http://ffmpeg.org/
FFMPEG_PATH = "ffmpeg"

from bilibili_my_favorite.services.bilibili_service import bilibili_service
from bilibili_my_favorite.core.bilibili_plus import get_download_url



async def main():
    bvid = "BV16Hj1zXEDU"
    page_index = 0

    if not bilibili_service.is_authenticated():
        print("未认证")
        os._exit(0) 

    credential = bilibili_service.credential

    # 实例化 Video 类
    v = video.Video(bvid=bvid, credential=credential)
    # info = await v.get_info()
    # print(info)
    cid = await v.get_cid(page_index)
    # print(f"cid: {cid}")
    # 获取视频下载链接
    download_url_data = await get_download_url(bvid=bvid, cid=cid, credential=credential, qn=80)
    # print(download_url_data)

    # 解析视频下载信息
    detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)
    streams = detecter.detect_best_streams()

    print(streams)

    # 有 MP4 流 / FLV 流两种可能
    if detecter.check_flv_mp4_stream() == True:
        temp_file_path = f"{config.VIDEOS_DIR}/{bvid}.temp.flv"

        # FLV 流下载
        await video_downloader.download_video(streams[0].url, temp_file_path, "下载 FLV 音视频流")
        # 转换文件格式
        os.system(f"{FFMPEG_PATH} -i {temp_file_path} {bvid}_{page_index}.mp4")
        # 删除临时文件
        os.remove(temp_file_path)
    else:
        video_temp_file_path = f"{config.VIDEOS_DIR}/{bvid}.video_temp.m4s"
        audio_temp_file_path = f"{config.VIDEOS_DIR}/{bvid}.audio_temp.m4s"

        # MP4 流下载
        await video_downloader.download_video(streams[0].url, video_temp_file_path, "下载视频流")
        await video_downloader.download_video(streams[1].url, audio_temp_file_path, "下载音频流")
        # 混流
        os.system(
            f"{FFMPEG_PATH} -i {video_temp_file_path} -i {audio_temp_file_path} -vcodec copy -acodec copy {config.VIDEOS_DIR}/{bvid}_{page_index}.mp4"
        )
        # 删除临时文件
        os.remove(video_temp_file_path)
        os.remove(audio_temp_file_path)

    print(f"已下载为：{config.VIDEOS_DIR}/{bvid}_{page_index}.mp4")


if __name__ == "__main__":
    # 主入口
    asyncio.run(main())