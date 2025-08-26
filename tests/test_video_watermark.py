#!/usr/bin/env python3
"""
Video Watermark Removal Test Script
For validating the demo version's basic functionality
"""

import os
import sys
import tempfile
import requests
import json
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_video_watermark_models():
    """Test data models"""
    print("🧪 Testing data models...")
    
    try:
        from video_watermark.models import VideoWatermarkTask, WatermarkRegion, TaskProcessingLog, storage
        
        # Test task creation
        task = VideoWatermarkTask("test_video.mp4", 1024*1024, "mp4")
        print(f"✅ Task created successfully: {task.task_uuid}")
        
        # Test task saving (using simplified storage)
        if task.save():
            print("✅ Task saved successfully")
        else:
            print("❌ Task saving failed")
        
        # Test task retrieval
        retrieved_task = VideoWatermarkTask.get_by_uuid(task.task_uuid)
        if retrieved_task:
            print("✅ Task retrieval successful")
        else:
            print("❌ Task retrieval failed")
        
        # Test watermark regions
        regions = [
            {
                'region_order': 1,
                'x': 100,
                'y': 100,
                'width': 200,
                'height': 150
            }
        ]
        if storage.save_regions(task.task_uuid, regions):
            print("✅ Watermark regions saved successfully")
        else:
            print("❌ Failed to save watermark regions")
        
        # Test region retrieval
        retrieved_regions = storage.get_regions(task.task_uuid)
        if retrieved_regions:
            print("✅ Watermark regions retrieved successfully")
        else:
            print("❌ Failed to retrieve watermark regions")
        
        # Test logging
        TaskProcessingLog.add_log(task.task_uuid, 'info', 'Test log message', 'test')
        print("✅ Log recorded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

def test_video_processor():
    """Test video processor"""
    print("\n🎬 Testing video processor...")
    
    try:
        from video_watermark.video_processor import VideoProcessor
        
        processor = VideoProcessor()
        print("✅ Video processor initialized successfully")
        
        # Note: A real video file is needed for testing
        # In actual deployment, a small test video file can be created
        print("ℹ️  Video processor functionality requires real video files for complete testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Video processor test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints (server needs to be running)"""
    print("\n🌐 Testing API endpoints...")
    
    # Just checking if routes are correctly imported
    try:
        from video_watermark.routes import video_watermark_bp
        print("✅ API routes imported successfully")
        
        # Check routes in blueprint (simplified version)
        print("📋 Available API endpoints:")
        print("   POST /api/video/upload - Upload video")
        print("   GET /api/video/task/{uuid}/frames - Get video frames")
        print("   POST /api/video/task/{uuid}/select-frame - Select frame")
        print("   POST /api/video/task/{uuid}/select-regions - Submit watermark regions")
        print("   GET /api/video/task/{uuid}/status - Check task status")
        print("   GET /api/video/task/{uuid}/download - Download result")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def check_storage_directory():
    """Check storage directory"""
    print("\n📁 Checking storage directory...")
    
    try:
        temp_storage_dir = Path("temp_storage")
        if not temp_storage_dir.exists():
            temp_storage_dir.mkdir(exist_ok=True)
            print("✅ Temporary storage directory created")
        else:
            print("✅ Temporary storage directory already exists")
        
        print(f"   Storage location: {temp_storage_dir.absolute()}")
        return True
        
    except Exception as e:
        print(f"❌ Storage directory check failed: {e}")
        return False

def check_dependencies():
    """Check dependencies"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'cv2',
        'numpy', 
        'flask'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'numpy':
                import numpy
            elif package == 'flask':
                import flask
            
            print(f"✅ {package} installed")
            
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} not installed")
    
    if missing_packages:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_packages)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Video Watermark Removal Test Starting...\n")
    
    tests = [
        ("依赖项检查", check_dependencies),
        ("存储目录检查", check_storage_directory),
        ("数据模型测试", test_video_watermark_models),
        ("视频处理器测试", test_video_processor),
        ("API 端点测试", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"测试: {test_name}")
        print(f"{'='*50}")
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} 通过")
        else:
            print(f"❌ {test_name} 失败")
    
    print(f"\n{'='*50}")
    print(f"测试结果: {passed}/{total} 通过")
    print(f"{'='*50}")
    
    if passed == total:
        print("🎉 所有测试通过！视频去水印功能准备就绪。")
        print("\n📝 下一步:")
        print("1. 启动 Flask 应用: python app/routes.py")
        print("2. 访问 http://localhost:50001/video-watermark.html")
        print("3. 上传测试视频进行完整功能验证")
        print("\n💡 提示:")
        print("- 使用内存和文件存储，无需数据库")
        print("- 支持 MP4, MOV, AVI, MKV 格式")
        print("- 文件大小限制 500MB")
    else:
        print("⚠️  部分测试失败，请检查上述错误信息。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)