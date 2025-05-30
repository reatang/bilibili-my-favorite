"""
简单的视频信息获取测试
直接调用bilibili_service.get_video_info方法
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bilibili_my_favorite.services.bilibili_service import bilibili_service


async def simple_test():
    """简单测试get_video_info方法"""
    
    # 要测试的视频BVID
    bvid = "BV1sPtWeiE6H"  # 请替换为实际的BVID
    
    print(f"正在获取视频 {bvid} 的信息...")
    
    try:
        # 直接调用get_video_info方法
        video_info = await bilibili_service.get_video_info(bvid)
        
        if video_info:
            print("✅ 获取成功!")
            print(f"标题: {video_info.get('title')}")
            print(f"UP主: {video_info.get('owner', {}).get('name')}")
            print(f"播放量: {video_info.get('stat', {}).get('view')}")
            print(f"时长: {video_info.get('duration')} 秒")
        else:
            print("❌ 获取失败")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    asyncio.run(simple_test()) 