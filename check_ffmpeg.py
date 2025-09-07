#!/usr/bin/env python3
"""
FFmpeg Installation Check Script for MediaCraft
检查生产环境FFmpeg安装状态
"""
import subprocess
import sys
import os
from core.utils import check_ffmpeg_availability

def check_ffmpeg_detailed():
    """检查FFmpeg是否安装并可用（详细版本）"""
    print("🔍 检查FFmpeg安装状态...")
    
    # 使用共享的检查函数
    if not check_ffmpeg_availability():
        print("❌ FFmpeg未安装或不在PATH中")
        return False
        
    try:
        # 获取版本信息
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # 解析版本信息
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg已安装: {version_line}")
            
            # 检查编解码器支持
            codec_result = subprocess.run(['ffmpeg', '-codecs'], 
                                        capture_output=True, text=True, timeout=10)
            
            required_codecs = ['h264', 'aac', 'mp4']
            missing_codecs = []
            
            for codec in required_codecs:
                if codec not in codec_result.stdout.lower():
                    missing_codecs.append(codec)
            
            if missing_codecs:
                print(f"⚠️  缺少编解码器支持: {', '.join(missing_codecs)}")
                return False
            else:
                print("✅ 所有必需的编解码器都已支持")
                return True
                
        else:
            print(f"❌ FFmpeg命令执行失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 检查FFmpeg时出错: {e}")
        return False

def print_installation_instructions():
    """打印安装说明"""
    print("\n📋 FFmpeg安装说明:")
    print("Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
    print("CentOS/RHEL:   sudo yum install ffmpeg  (或 sudo dnf install ffmpeg)")
    print("macOS:         brew install ffmpeg")
    print("\n验证安装:")
    print("ffmpeg -version")
    print("which ffmpeg")

def main():
    """主函数"""
    print("🎬 MediaCraft FFmpeg 检查工具")
    print("=" * 50)
    
    if check_ffmpeg_detailed():
        print("\n🎉 FFmpeg检查通过！视频合并功能可以正常使用。")
        sys.exit(0)
    else:
        print("\n💥 FFmpeg检查失败！视频合并功能将无法使用。")
        print_installation_instructions()
        sys.exit(1)

if __name__ == "__main__":
    main()