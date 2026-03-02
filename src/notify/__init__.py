"""
消息推送模块
支持 Server 酱、邮件等多种推送方式
"""

from src.notify.serverchan import ServerChanNotifier

__all__ = ['ServerChanNotifier']
