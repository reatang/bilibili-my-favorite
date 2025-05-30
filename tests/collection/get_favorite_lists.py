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
    """简单测试get_favorite_lists方法"""
    
    
    try:
        # 直接调用get_favorite_lists方法
        favorite_lists = await bilibili_service.get_favorite_lists()
        
        if favorite_lists:
            print("✅ 获取成功!")
            print(f"收藏夹列表: {favorite_lists}")
        else:
            print("❌ 获取失败")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    asyncio.run(simple_test()) 