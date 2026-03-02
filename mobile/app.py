# -*- coding: utf-8 -*-
"""
尾盘选股器 - Android 移动版
使用 Kivy 框架开发的移动端应用
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

# 设置窗口大小（模拟手机屏幕）
Window.size = (360, 640)

import pandas as pd
from src.strategies.tail_strategy import TailStockStrategy
from src.theme_heat_engine import ThemeHeatEngine
from src.data_sources.eastmoney_themes import EastmoneyThemeCrawler
from src.akshare_api import get_all_stocks_realtime, get_individual_fund_flow


class StockItem(RecycleBoxLayout):
    """股票列表项布局"""
    pass


class StockRV(RecycleView):
    """股票列表 RecycleView"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.viewclass = 'StockItem'
        self.data = []


class HomeScreen(Screen):
    """首页"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # 标题
        title = Label(
            text='尾盘选股器',
            size_hint=(1, 0.15),
            font_size=dp(24),
            bold=True
        )
        self.layout.add_widget(title)

        # 日期显示
        self.date_label = Label(
            text=datetime.now().strftime('%Y-%m-%d'),
            size_hint=(1, 0.1),
            font_size=dp(16)
        )
        self.layout.add_widget(self.date_label)

        # 状态显示
        self.status_label = Label(
            text='就绪',
            size_hint=(1, 0.1),
            font_size=dp(14),
            color=(0.5, 0.5, 0.5, 1)
        )
        self.layout.add_widget(self.status_label)

        # 选股按钮
        self.pick_button = Button(
            text='开始选股',
            size_hint=(1, 0.15),
            font_size=dp(18),
            background_color=(0.2, 0.6, 0.2, 1)
        )
        self.pick_button.bind(on_press=self.start_pick)
        self.layout.add_widget(self.pick_button)

        # 查看结果按钮
        self.result_button = Button(
            text='查看结果',
            size_hint=(1, 0.15),
            font_size=dp(18),
            background_color=(0.2, 0.4, 0.8, 1)
        )
        self.result_button.bind(on_press=self.go_to_result)
        self.layout.add_widget(self.result_button)

        self.add_widget(self.layout)

    def start_pick(self, instance):
        """开始选股"""
        self.status_label.text = '正在获取数据...'
        self.pick_button.disabled = True

        # 延迟执行，避免 UI 卡顿
        Clock.schedule_once(lambda dt: self.run_pick(), 0.1)

    def run_pick(self):
        """执行选股逻辑"""
        try:
            # 获取数据
            self.status_label.text = '获取行情数据...'
            all_data = get_all_stocks_realtime()

            if all_data is None or all_data.empty:
                self.status_label.text = '获取数据失败'
                self.pick_button.disabled = False
                return

            # 获取资金流
            self.status_label.text = '获取资金流...'
            fund_flow = get_individual_fund_flow()

            # 获取板块热度
            self.status_label.text = '计算板块热度...'
            theme_heat_dict = {}
            hot_themes = []
            try:
                crawler = EastmoneyThemeCrawler()
                engine = ThemeHeatEngine(data_source=crawler)
                hot_df, components = engine.get_hot_themes_with_components(top_n=10)
                if not hot_df.empty:
                    for _, row in hot_df.iterrows():
                        theme_heat_dict[row['板块名称']] = min(100, row['热度评分'])
                    hot_themes = hot_df['板块名称'].head(5).tolist()
            except Exception as e:
                print(f"板块热度获取失败：{e}")

            # 创建选股器
            picker = TailStockStrategy()
            picker.set_fund_flow_data(fund_flow)
            if theme_heat_dict:
                picker.set_theme_heat(theme_heat_dict)
                picker.HOT_THEMES = hot_themes
                picker.set_dynamic_components(components)

            # 执行选股
            self.status_label.text = '执行选股策略...'
            result = picker.select(all_data)

            if result.empty:
                self.status_label.text = '未找到符合条件的股票'
            else:
                # 保存结果
                app = App.get_running_app()
                app.current_result = result
                app.save_current_result()
                self.status_label.text = f'选股完成！共 {len(result)} 只'

        except Exception as e:
            self.status_label.text = f'错误：{str(e)}'

        self.pick_button.disabled = False

    def go_to_result(self, instance):
        """跳转到结果页"""
        app = App.get_running_app()
        if app.current_result is not None:
            self.manager.current = 'result'
            self.manager.get_screen('result').update_result()
        else:
            self.status_label.text = '请先选股'


class ResultScreen(Screen):
    """结果页"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # 标题
        title = Label(
            text='选股结果',
            size_hint=(1, 0.1),
            font_size=dp(20),
            bold=True
        )
        self.layout.add_widget(title)

        # 股票列表
        self.rv = StockRV()
        self.rv.size_hint = (1, 0.8)
        self.layout.add_widget(self.rv)

        # 返回按钮
        back_btn = Button(
            text='返回',
            size_hint=(1, 0.1),
            font_size=dp(16)
        )
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        self.layout.add_widget(back_btn)

        self.add_widget(self.layout)

    def update_result(self):
        """更新结果列表"""
        app = App.get_running_app()
        if app.current_result is None:
            self.rv.data = []
            return

        df = app.current_result
        data = []

        # 确定列
        name_col = '名称' if '名称' in df.columns else None
        code_col = '代码' if '代码' in df.columns else None
        gain_col = '涨跌幅' if '涨跌幅' in df.columns else ('涨幅' if '涨幅' in df.columns else None)
        theme_col = '所属题材' if '所属题材' in df.columns else None

        for _, row in df.head(20).iterrows():
            name = row.get(name_col, 'N/A') if name_col else ''
            code = row.get(code_col, 'N/A') if code_col else ''
            gain = row.get(gain_col, 0) if gain_col else 0
            theme = row.get(theme_col, '') if theme_col else ''

            item = {
                'text': f'{name}({code})\n涨幅：{gain:.2f}%' + (f'  题材：{theme}' if theme else ''),
            }
            data.append(item)

        self.rv.data = data


class SettingsScreen(Screen):
    """设置页"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # 标题
        title = Label(
            text='设置',
            size_hint=(1, 0.1),
            font_size=dp(20),
            bold=True
        )
        self.layout.add_widget(title)

        # 关于
        about = Label(
            text='尾盘选股器 v3.1\n题材热点增强版\n\n功能:\n- 尾盘选股策略\n- 板块热度分析\n- 题材热点追踪',
            size_hint=(1, 0.5),
            font_size=dp(14),
            halign='center'
        )
        self.layout.add_widget(about)

        # 返回按钮
        back_btn = Button(
            text='返回',
            size_hint=(1, 0.1),
            font_size=dp(16)
        )
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        self.layout.add_widget(back_btn)

        self.add_widget(self.layout)


class StockPickerApp(App):
    """尾盘选股器 App"""

    current_result = None

    def build(self):
        self.title = '尾盘选股器'

        # 创建屏幕管理器
        sm = ScreenManager()

        # 添加屏幕
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(SettingsScreen(name='settings'))

        return sm

    def save_current_result(self):
        """保存当前选股结果到本地"""
        if self.current_result is None:
            return

        from pathlib import Path
        output_dir = Path('/sdcard/Android/data/com.tailpicker/files/stock_data') if platform == 'android' else Path('stock_data/tail_pick')
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = output_dir / f"pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.current_result.to_csv(filename, index=False, encoding='utf-8-sig')

    def on_pause(self):
        """Android 后台暂停"""
        return True

    def on_resume(self):
        """Android 恢复前台"""
        pass


# Android 平台检测
try:
    from android import platform
except ImportError:
    platform = 'desktop'


if __name__ == '__main__':
    StockPickerApp().run()
