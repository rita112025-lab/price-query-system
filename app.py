#!/usr/bin/env python3
"""
Hugging Face Spaces 應用入口點
如果在 Python / Streamlit 環境中執行，會啟動 streamlit_app.py。
"""

import os
import subprocess
import sys

APP_FILE = os.path.join(os.path.dirname(__file__), 'streamlit_app.py')


def print_startup_info():
    print("=" * 50)
    print("英建工程 材料價格查詢系統")
    print("=" * 50)
    print("\n✅ 應用已啟動")
    print("\n📋 系統檢查：")

    db_pass = os.getenv('DB_PASS')
    hf_token = os.getenv('HUGGINGFACE_TOKEN')

    print(f"  • DB_PASS: {'✓ 已設定' if db_pass else '✗ 未設定'}")
    print(f"  • HUGGINGFACE_TOKEN: {'✓ 已設定' if hf_token else '⚠ 未設定 (可選)'}")

    port = os.getenv('PORT', '7860')
    print("\n🌐 Web 應用運行在：")
    print(f"  • http://localhost:{port}")
    print("\n✨ 功能：")
    print("  • 材料價格查詢")
    print("  • Excel 檔案匯入")
    print("  • 批次刪除")
    print("  • CSV 匯出")
    print("\n" + "=" * 50)


if __name__ == '__main__':
    print_startup_info()

    if not os.path.exists(APP_FILE):
        print(f"錯誤：未找到 {APP_FILE}")
        sys.exit(1)

    try:
        subprocess.run([
            sys.executable,
            '-m',
            'streamlit',
            'run',
            APP_FILE,
            '--server.port',
            os.getenv('PORT', '7860'),
            '--server.address',
            '0.0.0.0'
        ], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Streamlit 啟動失敗：{exc}")
        sys.exit(exc.returncode)
