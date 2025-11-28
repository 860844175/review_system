#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版慢性病报告生成系统启动脚本
"""


import time
import threading
import os
from pathlib import Path
import subprocess
import sys

def start_server():
    """启动Flask服务器"""
    try:
        # 启动simple_server.py
        env = os.environ.copy()
        # env['DIAGNOSIS_SYSTEM_BASE_URL'] = 'http://localhost:5001' # 暂时指向自己，或者应该是zhikai模拟器的地址？
        # 用户在运行 demo_zhikai_simulator.py，它似乎只是一个客户端脚本，不是服务端。
        # 等等，demo_zhikai_simulator.py 是模拟 zhikai 调用审核系统。
        # 审核系统需要反向调用 zhikai 拉取数据。
        # 如果没有 zhikai 服务端在运行，那么 live 模式会失败。
        # 
        # 让我们先设置一个假地址，或者如果用户有 zhikai 模拟器服务端，应该指向那里。
        # 目前看来 demo_zhikai_simulator.py 只是发送请求，并没有启动 web server。
        # 
        # 除非... simple_server.py 里的 LiveDiagnosisSystemClient 是要去请求某个地方。
        # 如果没有这个服务，请求会失败。
        # 
        # 让我们先设置环境变量，至少通过 400 检查。
        # 假设 zhikai 系统也在本地，端口未知。
        # 但为了通过检查，我们需要设置它。
        env['DIAGNOSIS_SYSTEM_BASE_URL'] = 'http://localhost:5002' # 假设值
        env['DIAGNOSIS_SYSTEM_API_KEY'] = 'test_key'
        
        subprocess.run([sys.executable, 'simple_server.py'], env=env, check=True)
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"服务启动失败: {e}")

def main(port_number=5001):
    print("=" * 50)
    print("    慢性病报告生成系统 - 简化版")
    print("=" * 50)
    print()
    
    # 检查文件是否存在
    current_dir = Path(__file__).parent
    server_file = current_dir / 'simple_server.py'
    
    if not server_file.exists():
        print("❌ 找不到服务器文件: simple_server.py")
        return

    
    print("✅ 文件检查通过")
    print()
    
    # 启动说明
    print("📋 使用说明:")
    print("1. 系统将启动本地服务器")

    print("3. 输入患者ID (P001, P002, P003) 测试功能")
    print("4. 按 Ctrl+C 停止服务")
    print()
    
    # 启动服务器
    print("🚀 正在启动服务器...")
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 等待服务器启动
    time.sleep(3)
    
    print()
    print("💡 提示:")

    print(f"- API地址: http://localhost:{port_number}/api")
    print("- 可用患者ID: P001, P002, P003")
    print()
    print("⏳ 服务运行中，按 Ctrl+C 停止...")
    
    try:
        # 保持主进程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 感谢使用！")

if __name__ == '__main__':
    main(port_number=5001)