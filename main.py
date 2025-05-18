import asyncio
from bilibili_api import video, Credential, favorite_list, select_client, request_settings
from rich import print
import os
import json
import random
import glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
select_client("curl_cffi")

request_settings.set("impersonate", "chrome136")

uid = os.getenv("USESR_DEDE_USER_ID")
save_path = f"favorite/{uid}"

# 实例化 Credential 类
credential = Credential(
    sessdata=os.getenv("USER_SESSDATA"),
    bili_jct=os.getenv("USER_BILI_JCT"),
    buvid3=os.getenv("USER_BUVID3"),
    ac_time_value=os.getenv("USER_AC_TIME_VALUE"),
)

async def load_favorite_list(favorite_id: int, save_dir: str) -> list[dict]:
    has_more = True
    page = 1
    media_list = []
    while has_more:
        # 随机500ms ~ 3000ms
        await asyncio.sleep(random.randint(500, 3000) / 1000)

        # 获取收藏夹内容
        result = await favorite_list.get_video_favorite_list_content(media_id=favorite_id, page=page, credential=credential)
        if not result["medias"]:
            break

        # 临时文件
        temp_file = f"{save_dir}/temp/page_{page}.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        has_more = result["has_more"]
        page += 1
        media_list.extend(result["medias"])

    return media_list

# 本地加载收藏夹内容（用于测试）
def local_load_favorite_list(favorite_id: int, save_dir: str) -> list[dict]:
    # 读取所有temp文件  
    temp_files = glob.glob(f"{save_dir}/temp/*.json")
    media_list = []
    for temp_file in temp_files:
        with open(temp_file, "r", encoding="utf-8") as f:
            media_list.extend(json.load(f)["medias"])
    return media_list

# 获取我的收藏夹
async def my_favorite() -> None:
    result = await favorite_list.get_video_favorite_list(uid=uid, credential=credential)
    run_time = datetime.now()
    
    # 拉取数据
    for favorite in result["list"]:
        # 创建文件夹
        save_dir = f"{save_path}/{favorite['id']}-{favorite['title']}"
        os.makedirs(f"{save_dir}/temp", exist_ok=True)

        media_list = await load_favorite_list(favorite["id"], save_dir)
        # media_list = local_load_favorite_list(favorite["id"], save_dir)

        # 检测是否存在latest_content.json，如果有，则修改为 backup_{Y-m-d_H-M-S}.json
        has_latest_content = os.path.exists(f"{save_dir}/latest_content.json")
        backup_file_name = f"backup_{run_time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        backup_file_content = []
        if has_latest_content:
            os.rename(f"{save_dir}/latest_content.json", f"{save_dir}/{backup_file_name}")
            with open(f"{save_dir}/{backup_file_name}", "r", encoding="utf-8") as f:
                backup_file_content = json.load(f)

        # 保存新的latest_content.json
        with open(f"{save_dir}/latest_content.json", "w", encoding="utf-8") as f:
            json.dump(media_list, f, ensure_ascii=False)

        # 如果有backup_file_content则进行对比，如果backup_file_content中的视频title不是“已失效视频”，但是latest_content.json中的视频title是“已失效视频”，则输出
        delete_list = []
        if has_latest_content:
            for latest_media in media_list:
                # 是否存在于backup_file_content中
                for backup_media in backup_file_content:
                    if latest_media["bv_id"] == backup_media["bv_id"]:
                        if backup_media["title"] != "已失效视频" and latest_media["title"] == "已失效视频":
                            delete_list.append(backup_media)
                            print(f"收藏夹：{favorite['title']}, {backup_media['title']} 已失效, bvid: {backup_media['bv_id']}, up主: {backup_media['upper']['name']}")
        else:
            # 第一次跑，将所有title为“已失效视频”都装入delete_list
            for latest_media in media_list:
                if latest_media["title"] == "已失效视频":
                    delete_list.append(latest_media)
                    print(f"收藏夹：{favorite['title']}, {latest_media['title']} 已失效, bvid: {latest_media['bv_id']}, up主: {latest_media['upper']['name']}")

        # 存储已失效视频
        if len(delete_list) > 0:
            delete_file_name = f"{save_dir}/delete_list_{run_time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
            with open(delete_file_name, "w", encoding="utf-8") as f:
                json.dump(delete_list, f, ensure_ascii=False)


async def main() -> None:
    # 检测收藏夹被删除的视频
    await my_favorite()


if __name__ == "__main__":
    asyncio.run(main())
