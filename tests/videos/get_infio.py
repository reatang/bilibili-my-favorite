"""
测试通过bilibili_service获取视频信息
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.bilibili_my_favorite.services.bilibili_service import bilibili_service
from src.bilibili_my_favorite.core.config import config
from src.bilibili_my_favorite.utils.logger import logger


async def test_get_video_info():
    """测试获取单个视频信息"""
    
    # 检查B站API凭据是否配置
    if not config.validate_bilibili_credentials():
        print("❌ B站API凭据未配置完整，请检查以下环境变量：")
        print("- USER_DEDE_USER_ID")
        print("- USER_SESSDATA") 
        print("- USER_BILI_JCT")
        print("- USER_BUVID3")
        print("- USER_AC_TIME_VALUE (可选)")
        return
    
    # 测试视频BVID列表
    test_bvids = [
        "BV1sPtWeiE6H",  # 示例BVID，请替换为实际的BVID
        "BV1Ys41127cQ",  # 另一个示例BVID
    ]
    
    print("🚀 开始测试获取视频信息...")
    
    for bvid in test_bvids:
        print(f"\n📹 正在获取视频 {bvid} 的信息...")
        
        try:
            # 调用bilibili_service的get_video_info方法
            video_info = await bilibili_service.get_video_info(bvid)
            
            if video_info:
                print(f"✅ 成功获取视频信息:")
                print(f"   标题: {video_info.get('title', 'N/A')}")
                print(f"   BVID: {video_info.get('bvid', 'N/A')}")
                print(f"   AV号: {video_info.get('aid', 'N/A')}")
                print(f"   UP主: {video_info.get('owner', {}).get('name', 'N/A')}")
                print(f"   时长: {video_info.get('duration', 'N/A')} 秒")
                print(f"   播放量: {video_info.get('stat', {}).get('view', 'N/A')}")
                print(f"   点赞数: {video_info.get('stat', {}).get('like', 'N/A')}")
                print(f"   投币数: {video_info.get('stat', {}).get('coin', 'N/A')}")
                print(f"   收藏数: {video_info.get('stat', {}).get('favorite', 'N/A')}")
                print(f"   分享数: {video_info.get('stat', {}).get('share', 'N/A')}")
                print(f"   弹幕数: {video_info.get('stat', {}).get('danmaku', 'N/A')}")
                print(f"   发布时间: {video_info.get('pubdate', 'N/A')}")
                print(f"   简介: {video_info.get('desc', 'N/A')[:100]}...")
                
                # 显示视频分P信息
                pages = video_info.get('pages', [])
                if pages:
                    print(f"   分P数量: {len(pages)}")
                    for i, page in enumerate(pages[:3]):  # 只显示前3个分P
                        print(f"     P{i+1}: {page.get('part', 'N/A')}")
                    if len(pages) > 3:
                        print(f"     ... 还有 {len(pages) - 3} 个分P")
                
            else:
                print(f"❌ 获取视频 {bvid} 信息失败")
                
        except Exception as e:
            print(f"❌ 获取视频 {bvid} 信息时发生错误: {e}")
        
        # 添加延迟避免请求过快
        await asyncio.sleep(1)
    
    print("\n🎉 测试完成!")


async def test_get_video_info_with_custom_bvid():
    """测试获取用户指定的视频信息"""
    
    # 检查B站API凭据是否配置
    if not config.validate_bilibili_credentials():
        print("❌ B站API凭据未配置完整")
        return
    
    # 获取用户输入的BVID
    bvid = input("请输入要查询的视频BVID (例如: BV1xx411c7mD): ").strip()
    
    if not bvid:
        print("❌ 未输入BVID")
        return
    
    if not bvid.startswith("BV"):
        print("❌ BVID格式不正确，应该以'BV'开头")
        return
    
    print(f"\n📹 正在获取视频 {bvid} 的详细信息...")
    
    try:
        video_info = await bilibili_service.get_video_info(bvid)
        
        if video_info:
            print(f"\n✅ 视频信息获取成功!")
            print("=" * 50)
            print(f"标题: {video_info.get('title', 'N/A')}")
            print(f"BVID: {video_info.get('bvid', 'N/A')}")
            print(f"AV号: {video_info.get('aid', 'N/A')}")
            
            owner = video_info.get('owner', {})
            print(f"UP主: {owner.get('name', 'N/A')} (UID: {owner.get('mid', 'N/A')})")
            
            print(f"时长: {video_info.get('duration', 'N/A')} 秒")
            print(f"发布时间: {video_info.get('pubdate', 'N/A')}")
            
            stat = video_info.get('stat', {})
            print(f"播放量: {stat.get('view', 'N/A'):,}")
            print(f"点赞数: {stat.get('like', 'N/A'):,}")
            print(f"投币数: {stat.get('coin', 'N/A'):,}")
            print(f"收藏数: {stat.get('favorite', 'N/A'):,}")
            print(f"分享数: {stat.get('share', 'N/A'):,}")
            print(f"弹幕数: {stat.get('danmaku', 'N/A'):,}")
            
            desc = video_info.get('desc', '')
            if desc:
                print(f"简介: {desc[:200]}{'...' if len(desc) > 200 else ''}")
            
            # 显示标签
            tags = video_info.get('tags', [])
            if tags:
                tag_names = [tag.get('tag_name', '') for tag in tags[:5]]
                print(f"标签: {', '.join(tag_names)}")
            
            # 显示分P信息
            pages = video_info.get('pages', [])
            if pages:
                print(f"分P数量: {len(pages)}")
                for i, page in enumerate(pages):
                    print(f"  P{i+1}: {page.get('part', 'N/A')} (时长: {page.get('duration', 'N/A')}秒)")
            
            print("=" * 50)
            
        else:
            print(f"❌ 获取视频 {bvid} 信息失败，可能是视频不存在或已被删除")
            
    except Exception as e:
        print(f"❌ 获取视频信息时发生错误: {e}")


def main():
    """主函数"""
    print("B站视频信息获取测试")
    print("=" * 30)
    
    # 选择测试模式
    print("请选择测试模式:")
    print("1. 使用预设BVID测试")
    print("2. 输入自定义BVID测试")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_get_video_info())
    elif choice == "2":
        asyncio.run(test_get_video_info_with_custom_bvid())
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()
