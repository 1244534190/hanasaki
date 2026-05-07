import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.message_components import Reply, Node, Custom
from astrbot.api.star import Star, Context, register
from astrbot.api import logger

from .config import ConfigManager
from .utils import MessageParser, TimeParser

@register("chat_forward", "Hanasaki", "聊天记录合并转发插件", "1.0.0")
class ChatForwardPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any] = None):
        super().__init__(context)
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.message_parser = MessageParser()
        self.time_parser = TimeParser()
        
    @staticmethod
    def parse_command(message: str) -> tuple:
        """解析命令格式"""
        parts = message.strip().split()
        if len(parts) < 3:
            return None, None, None, None
        
        cmd = parts[0]
        target = parts[1]
        time_range = ' '.join(parts[2:])
        
        return cmd, target, time_range, parts
    
    async def get_messages_in_range(
        self, 
        session_id: str, 
        start_time: datetime, 
        end_time: datetime,
        limit: int = 100
    ) -> List[Dict]:
        """获取指定时间范围内的消息"""
        # 这里需要根据实际的消息存储实现
        # 示例：从context获取历史消息
        messages = []
        
        # 假设有消息历史存储
        if hasattr(self.context, 'get_message_history'):
            history = await self.context.get_message_history(session_id, limit=limit)
            for msg in history:
                msg_time = datetime.fromtimestamp(msg.get('time', 0))
                if start_time <= msg_time <= end_time:
                    messages.append(msg)
        
        return messages
    
    async def forward_to_target(
        self,
        target_type: str,
        target_id: str,
        messages: List[Dict]
    ):
        """转发消息到目标"""
        if not messages:
            return
        
        # 构建合并转发的消息节点
        nodes = []
        for msg in messages:
            node = Node(
                name=msg.get('sender_name', '用户'),
                uin=msg.get('sender_id', ''),
                content=msg.get('content', '')
            )
            nodes.append(node)
        
        # 发送合并转发消息
        if target_type == 'friend':
            await self.context.send_friend_message(target_id, nodes)
        elif target_type == 'group':
            await self.context.send_group_message(target_id, nodes)
    
    async def handle_forward_from(
        self, 
        event: AstrMessageEvent,
        source_type: str,
        source_id: str,
        time_range: str
    ) -> str:
        """处理转来命令：从指定源转发到当前聊天"""
        try:
            # 解析时间范围
            start_time, end_time = self.time_parser.parse_time_range(time_range)
            if not start_time or not end_time:
                return "❌ 时间格式错误！请使用：\n- 过去时间：30分钟前、2小时前、3天前\n- 具体时间：2024-01-01 到 2024-01-31"
            
            # 获取消息
            session_id = f"{source_type}_{source_id}"
            messages = await self.get_messages_in_range(session_id, start_time, end_time)
            
            if not messages:
                return f"❌ 未找到{start_time}到{end_time}之间的消息记录"
            
            # 转发到当前聊天
            current_chat_id = event.get_session_id()
            await self.forward_to_target(
                event.get_message_type(),
                current_chat_id,
                messages
            )
            
            return f"✅ 已转发 {len(messages)} 条消息到当前聊天"
            
        except Exception as e:
            logger.error(f"转发失败：{e}")
            return f"❌ 转发失败：{str(e)}"
    
    async def handle_forward_to(
        self,
        event: AstrMessageEvent,
        target_str: str,
        time_range: str
    ) -> str:
        """处理转去命令：从当前聊天转发到指定目标"""
        try:
            # 解析目标（支持多个，用|分隔）
            targets = target_str.split('|')
            
            # 解析时间范围
            start_time, end_time = self.time_parser.parse_time_range(time_range)
            if not start_time or not end_time:
                return "❌ 时间格式错误！"
            
            # 获取当前聊天的消息
            current_session = event.get_session_id()
            messages = await self.get_messages_in_range(current_session, start_time, end_time)
            
            if not messages:
                return f"❌ 未找到{start_time}到{end_time}之间的消息记录"
            
            # 转发到每个目标
            success_count = 0
            for target in targets:
                target = target.strip()
                if target.startswith('g'):
                    # 群聊
                    group_id = target[1:]
                    await self.forward_to_target('group', group_id, messages)
                    success_count += 1
                else:
                    # 好友
                    await self.forward_to_target('friend', target, messages)
                    success_count += 1
            
            return f"✅ 已转发 {len(messages)} 条消息到 {success_count} 个目标"
            
        except Exception as e:
            logger.error(f"转发失败：{e}")
            return f"❌ 转发失败：{str(e)}"
    
    async def check_permission(self, event: AstrMessageEvent) -> bool:
        """检查用户权限"""
        user_id = event.get_sender_id()
        
        # 检查是否是管理员
        if user_id in self.config.get('admins', []):
            return True
        
        # 检查是否在超级用户列表中
        super_users = self.config.get('super_users', [])
        if user_id in super_users:
            return True
        
        return False
    
    @register.command('转去')
    async def forward_to(self, event: AstrMessageEvent):
        """转去 QQ好友/群聊 时间范围"""
        if not await self.check_permission(event):
            yield event.plain_result("❌ 权限不足！只有管理员可以使用此命令")
            return
        
        message = event.message_str
        parts = message.split(maxsplit=2)
        
        if len(parts) < 3:
            yield event.plain_result(
                "❌ 命令格式错误！\n"
                "正确格式：/转去 QQ号|群号 时间范围\n"
                "示例：\n"
                "- /转去 123456 30分钟前\n"
                "- /转去 g123456 2小时前\n"
                "- /转去 123456|g789456 2024-01-01 到 2024-01-31"
            )
            return
        
        target = parts[1]
        time_range = parts[2]
        
        result = await self.handle_forward_to(event, target, time_range)
        yield event.plain_result(result)
    
    @register.command('转来')
    async def forward_from(self, event: AstrMessageEvent):
        """转来 QQ好友/群聊 时间范围"""
        if not await self.check_permission(event):
            yield event.plain_result("❌ 权限不足！只有管理员可以使用此命令")
            return
        
        message = event.message_str
        parts = message.split(maxsplit=2)
        
        if len(parts) < 3:
            yield event.plain_result(
                "❌ 命令格式错误！\n"
                "正确格式：/转来 QQ号|群号 时间范围\n"
                "示例：\n"
                "- /转来 123456 30分钟前\n"
                "- /转来 g123456 2小时前"
            )
            return
        
        source = parts[1]
        time_range = parts[2]
        
        # 判断源类型
        if source.startswith('g'):
            source_type = 'group'
            source_id = source[1:]
        else:
            source_type = 'friend'
            source_id = source
        
        result = await self.handle_forward_from(event, source_type, source_id, time_range)
        yield event.plain_result(result)
    
    @register.command('添加管理员')
    async def add_admin(self, event: AstrMessageEvent):
        """添加管理员 - 需要超级管理员权限"""
        user_id = event.get_sender_id()
        super_users = self.config.get('super_users', [])
        
        if user_id not in super_users:
            yield event.plain_result("❌ 权限不足！只有超级管理员可以添加管理员")
            return
        
        parts = event.message_str.split()
        if len(parts) != 2:
            yield event.plain_result("❌ 格式错误！正确格式：/添加管理员 QQ号")
            return
        
        new_admin = parts[1]
        if new_admin not in self.config['admins']:
            self.config['admins'].append(new_admin)
            self.config_manager.save_config(self.config)
            yield event.plain_result(f"✅ 已添加 {new_admin} 为管理员")
        else:
            yield event.plain_result(f"❌ {new_admin} 已经是管理员了")
    
    @register.command('移除管理员')
    async def remove_admin(self, event: AstrMessageEvent):
        """移除管理员 - 需要超级管理员权限"""
        user_id = event.get_sender_id()
        super_users = self.config.get('super_users', [])
        
        if user_id not in super_users:
            yield event.plain_result("❌ 权限不足！只有超级管理员可以移除管理员")
            return
        
        parts = event.message_str.split()
        if len(parts) != 2:
            yield event.plain_result("❌ 格式错误！正确格式：/移除管理员 QQ号")
            return
        
        admin_to_remove = parts[1]
        if admin_to_remove in self.config['admins']:
            self.config['admins'].remove(admin_to_remove)
            self.config_manager.save_config(self.config)
            yield event.plain_result(f"✅ 已移除 {admin_to_remove} 的管理员权限")
        else:
            yield event.plain_result(f"❌ {admin_to_remove} 不是管理员")
    
    @register.command('管理员列表')
    async def list_admins(self, event: AstrMessageEvent):
        """查看管理员列表"""
        if not await self.check_permission(event):
            yield event.plain_result("❌ 权限不足")
            return
        
        admins = self.config.get('admins', [])
        super_users = self.config.get('super_users', [])
        
        result = "📋 管理员列表：\n"
        result += f"超级管理员：{', '.join(super_users) if super_users else '无'}\n"
        result += f"普通管理员：{', '.join(admins) if admins else '无'}"
        
        yield event.plain_result(result)