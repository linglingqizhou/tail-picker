"""
尾盘选股器 - 数据导出模块
支持 CSV、Excel、JSON 格式导出，以及推送消息格式
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class DataExporter:
    """数据导出器"""

    def __init__(self, output_dir: str = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "stock_data" / "tail_pick"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        导出为 CSV

        Args:
            df: DataFrame
            filename: 文件名，默认自动生成

        Returns:
            str: 保存路径
        """
        if filename is None:
            filename = f"pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return str(filepath)

    def export_excel(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        导出为 Excel

        Args:
            df: DataFrame
            filename: 文件名

        Returns:
            str: 保存路径
        """
        try:
            import xlsxwriter

            if filename is None:
                filename = f"pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            filepath = self.output_dir / filename

            # 创建 Excel  writer
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheetname='选股结果')

                # 获取 workbook 和 worksheet
                workbook = writer.book
                worksheet = writer.sheets['选股结果']

                # 添加格式
                header_fmt = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })

                # 设置列宽
                for i, col in enumerate(df.columns):
                    worksheet.set_column(i, i, 12)

            return str(filepath)

        except ImportError:
            print("安装 xlsxwriter 以导出 Excel: pip install xlsxwriter")
            return self.export_csv(df, filename.replace('.xlsx', '.csv'))

    def export_json(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        导出为 JSON

        Args:
            df: DataFrame
            filename: 文件名

        Returns:
            str: 保存路径
        """
        if filename is None:
            filename = f"pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.output_dir / filename

        # 转换为 JSON 格式
        records = df.to_dict('records')

        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def export_for_push(self, df: pd.DataFrame, top_n: int = 10, show_themes: bool = False) -> str:
        """
        导出为推送消息格式（微信/邮件）

        Args:
            df: DataFrame
            top_n: 显示前 N 只
            show_themes: 是否显示所属题材

        Returns:
            str: 推送消息文本
        """
        lines = []
        lines.append("=" * 50)
        lines.append(f"[尾盘选股] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 50)
        lines.append("")

        # 取前 N 只
        display_df = df.head(top_n).copy()

        # 尝试获取列（兼容不同列名）
        name_col = '名称' if '名称' in df.columns else ('name' if 'name' in df.columns else None)
        code_col = '代码' if '代码' in df.columns else ('symbol' if 'symbol' in df.columns else None)
        gain_col = '涨跌幅' if '涨跌幅' in df.columns else ('涨幅' if '涨幅' in df.columns else ('change_percent' if 'change_percent' in df.columns else None))
        score_col = 'score' if 'score' in df.columns else None
        theme_col = '所属题材' if '所属题材' in df.columns else None

        for i, (_, row) in enumerate(display_df.iterrows(), 1):
            name = row.get(name_col, 'N/A') if name_col else 'N/A'
            code = row.get(code_col, 'N/A') if code_col else 'N/A'
            gain = row.get(gain_col, 0) if gain_col else 0
            score = row.get(score_col, 0) if score_col else 0
            theme = row.get(theme_col, '') if (theme_col and show_themes) else ''

            lines.append(f"{i}. {name}({code})")
            if theme and show_themes:
                lines.append(f"   涨幅：{gain:.2f}%  评分：{score:.1f}  题材：{theme}")
            else:
                lines.append(f"   涨幅：{gain:.2f}%  评分：{score:.1f}")
            lines.append("")

        lines.append("=" * 50)
        lines.append("⚠️ 风险提示：选股仅供参考，不构成投资建议")
        lines.append("=" * 50)

        return "\n".join(lines)

    def export_history(self, all_results: List[pd.DataFrame]) -> str:
        """
        导出历史选股记录（用于回测分析）

        Args:
            all_results: 多次选股结果的列表

        Returns:
            str: 保存路径
        """
        # 合并所有结果
        if not all_results:
            return ""

        combined = pd.concat(all_results, ignore_index=True)

        filename = f"pick_history_{datetime.now().strftime('%Y%m')}.csv"
        filepath = self.output_dir / "history" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        combined.to_csv(filepath, index=False, encoding='utf-8-sig')

        return str(filepath)


def export_result(df: pd.DataFrame, formats: List[str] = None):
    """
    便捷导出函数

    Args:
        df: DataFrame
        formats: 导出格式列表 ['csv', 'excel', 'json', 'push']
    """
    if formats is None:
        formats = ['csv', 'push']

    exporter = DataExporter()
    files = []

    if 'csv' in formats:
        path = exporter.export_csv(df)
        files.append(('CSV', path))
        print(f"CSV 已保存：{path}")

    if 'excel' in formats:
        path = exporter.export_excel(df)
        files.append(('Excel', path))
        print(f"Excel 已保存：{path}")

    if 'json' in formats:
        path = exporter.export_json(df)
        files.append(('JSON', path))
        print(f"JSON 已保存：{path}")

    if 'push' in formats:
        msg = exporter.export_for_push(df)
        print("\n" + msg)

    return files


if __name__ == "__main__":
    # 测试导出功能
    print("测试数据导出功能")

    # 创建测试数据
    test_df = pd.DataFrame({
        '代码': ['000001', '000002', '600519'],
        '名称': ['平安银行', '万科 A', '贵州茅台'],
        '涨跌幅': [3.5, 4.2, 5.8],
        '量比': [1.8, 2.1, 1.5],
        '换手率': [5.2, 6.8, 2.1],
        '主力净流入 (万)': [800, 1200, 2500],
        'score': [85.5, 88.2, 92.0]
    })

    print("\n测试数据:")
    print(test_df.to_string())

    print("\n导出测试:")
    export_result(test_df, formats=['csv', 'push'])
