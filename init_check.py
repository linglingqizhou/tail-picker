"""
系统初始化检查脚本
"""

import sys
import os
import io

# 设置 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("           A 股行情数据采集系统 - 初始化检查")
print("=" * 60)
print()

# 检查依赖包
print("[1/4] 检查依赖包...")
try:
    import akshare
    print(f"  [OK] akshare {akshare.__version__}")
except ImportError:
    print("  [FAIL] akshare 未安装")

try:
    import pandas
    print(f"  [OK] pandas {pandas.__version__}")
except ImportError:
    print("  [FAIL] pandas 未安装")

try:
    import requests
    print(f"  [OK] requests {requests.__version__}")
except ImportError:
    print("  [FAIL] requests 未安装")

try:
    import tabulate
    print(f"  [OK] tabulate {tabulate.__version__}")
except ImportError:
    print("  [FAIL] tabulate 未安装")

# 检查目录结构
print()
print("[2/4] 检查目录结构...")
dirs = ["src", "stock_data/daily", "stock_data/minute", "stock_data/realtime"]
for d in dirs:
    if os.path.exists(d):
        print(f"  [OK] {d}/")
    else:
        print(f"  [FAIL] {d}/ 不存在")

# 检查文件
print()
print("[3/4] 检查关键文件...")
files = ["src/akshare_api.py", "src/sina_api.py", "src/data_collector.py", "config.py", "早盘扫描.bat"]
for f in files:
    if os.path.exists(f):
        print(f"  [OK] {f}")
    else:
        print(f"  [FAIL] {f} 不存在")

# 快速测试接口
print()
print("[4/4] 测试数据接口...")
try:
    sys.path.insert(0, ".")
    from src.akshare_api import get_all_stocks_realtime
    df = get_all_stocks_realtime()
    if df is not None and not df.empty:
        print(f"  [OK] AkShare 接口正常 (获取 {len(df)} 只股票)")
    else:
        print("  [FAIL] AkShare 接口返回空数据")
except Exception as e:
    print(f"  [FAIL] AkShare 接口错误：{e}")

try:
    from src.sina_api import SinaStockAPI
    api = SinaStockAPI()
    data = api.get_realtime("600519")
    if data:
        print(f"  [OK] 新浪财经接口正常 (贵州茅台：{data['current']}元)")
    else:
        print("  [FAIL] 新浪财经接口返回空数据")
except Exception as e:
    print(f"  [FAIL] 新浪财经接口错误：{e}")

print()
print("=" * 60)
print("                    初始化完成!")
print("=" * 60)
print()
print("使用方法:")
print("  1. 双击 早盘扫描.bat 运行早盘扫描")
print("  2. 或运行：python src/data_collector.py --mode morning")
print()
print("数据保存位置：D:\\\\cursor\\\\stock_data\\\\")
print("=" * 60)
