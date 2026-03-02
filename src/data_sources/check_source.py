# -*- coding: utf-8 -*-
"""
数据源配置工具
自动检测可用数据源并提供统一接口
"""

import requests
from typing import Optional, Dict


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        self.available_sources = {}
        self._check_sources()

    def _check_sources(self):
        """检查所有数据源的可用性"""
        sources = {
            'tencent': self._check_tencent,
            'eastmoney': self._check_eastmoney,
            'sina': self._check_sina,
            'cls': self._check_cls,
        }

        for name, check_func in sources.items():
            try:
                self.available_sources[name] = check_func()
            except:
                self.available_sources[name] = False

    def _check_tencent(self) -> bool:
        """检查腾讯 API"""
        try:
            resp = requests.get('http://qt.gtimg.cn/q=sh600519', timeout=5)
            return resp.status_code == 200 and '600519' in resp.text
        except:
            return False

    def _check_eastmoney(self) -> bool:
        """检查东方财富 API"""
        try:
            resp = requests.get('http://www.eastmoney.com/', timeout=5)
            return resp.status_code == 200
        except:
            return False

    def _check_sina(self) -> bool:
        """检查新浪 API"""
        try:
            resp = requests.get('http://hq.sinajs.cn/list=sh600519', timeout=5,
                              headers={'Referer': 'http://finance.sina.com.cn/'})
            return resp.status_code == 200 and '600519' in resp.text
        except:
            return False

    def _check_cls(self) -> bool:
        """检查财联社 API"""
        try:
            resp = requests.get('https://api.cls.cn/v1/roll/get_roll_list?limit=1', timeout=5)
            return resp.status_code == 200
        except:
            return False

    def get_status(self) -> Dict[str, bool]:
        """获取所有数据源状态"""
        return self.available_sources

    def get_best_source(self) -> Optional[str]:
        """获取最佳可用数据源"""
        # 优先级：腾讯 > 新浪 > 东方财富 > 财联社
        priority = ['tencent', 'sina', 'eastmoney', 'cls']
        for name in priority:
            if self.available_sources.get(name):
                return name
        return None

    def print_status(self):
        """打印数据源状态"""
        print("=" * 50)
        print("数据源可用性状态")
        print("=" * 50)
        status_map = {
            'tencent': '腾讯财经',
            'eastmoney': '东方财富',
            'sina': '新浪财经',
            'cls': '财联社',
        }
        for name, cn_name in status_map.items():
            status = self.available_sources.get(name, False)
            symbol = '[OK]' if status else '[FAIL]'
            print(f"  {symbol} {cn_name}")
        print("=" * 50)
        best = self.get_best_source()
        if best:
            print(f"推荐使用：{status_map.get(best)}")
        else:
            print("警告：所有数据源都不可用!")


# DNS 检查工具
def check_dns(domain: str) -> bool:
    """检查域名 DNS 解析"""
    try:
        import socket
        ip = socket.gethostbyname(domain)
        print(f"  {domain}: OK ({ip})")
        return True
    except Exception as e:
        print(f"  {domain}: FAIL")
        return False


def check_all_dns():
    """检查所有财经 API 域名的 DNS 解析"""
    print("=" * 50)
    print("DNS 解析检查")
    print("=" * 50)
    domains = {
        '腾讯财经': 'qt.gtimg.cn',
        '东方财富': 'push2.eastmoney.com',
        '财联社': 'api.cls.cn',
        '新浪财经': 'hq.sinajs.cn',
    }
    for name, domain in domains.items():
        print(f"{name}:")
        check_dns(domain)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'dns':
        check_all_dns()
    else:
        manager = DataSourceManager()
        manager.print_status()

        print()
        print("如需修改 DNS 服务器，请运行:")
        print("  python src/data_sources/check_source.py dns")
        print("  或以管理员身份运行 change_dns.bat")
