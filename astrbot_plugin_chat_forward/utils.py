import re
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict

class TimeParser:
    """时间解析器"""
    
    def parse_time_range(self, time_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """解析时间范围字符串"""
        # 处理"过去时间"格式
        past_match = re.match(r'(\d+)\s*(分钟|小时|天|周|月)前', time_str)
        if past_match:
            value = int(past_match.group(1))
            unit = past_match.group(2)
            
            end_time = datetime.now()
            
            if unit == '分钟':
                start_time = end_time - timedelta(minutes=value)
            elif unit == '小时':
                start_time = end_time - timedelta(hours=value)
            elif unit == '天':
                start_time = end_time - timedelta(days=value)
            elif unit == '周':
                start_time = end_time - timedelta(weeks=value)
            elif unit == '月':
                start_time = end_time - timedelta(days=value*30)
            else:
                return None, None
            
            return start_time, end_time
        
        # 处理"指定时间范围"格式
        range_match = re.match(r'(\d{4}-\d{2}-\d{2})\s*到\s*(\d{4}-\d{2}-\d{2})', time_str)
        if range_match:
            start_str = range_match.group(1)
            end_str = range_match.group(2)
            
            try:
                start_time = datetime.strptime(start_str, '%Y-%m-%d')
                end_time = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)
                return start_time, end_time
            except:
                return None, None
        
        # 处理"从X到Y"格式
        if '到' in time_str:
            parts = time_str.split('到')
            if len(parts) == 2:
                # 尝试解析具体时间
                try:
                    start_time = self.parse_datetime(parts[0].strip())
                    end_time = self.parse_datetime(parts[1].strip())
                    if start_time and end_time:
                        return start_time, end_time
                except:
                    pass
        
        return None, None
    
    def parse_datetime(self, time_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%m-%d %H:%M',
            '%H:%M:%S',
            '%H:%M'
        ]
        
        for fmt in formats:
            try:
                if fmt == '%H:%M' or fmt == '%H:%M:%S':
                    # 如果是时间，默认使用今天的日期
                    dt = datetime.strptime(time_str, fmt)
                    today = datetime.now().date()
                    return datetime.combine(today, dt.time())
                else:
                    return datetime.strptime(time_str, fmt)
            except:
                continue
        
        return None

class MessageParser:
    """消息解析器"""
    
    def extract_mentions(self, content: str) -> List[str]:
        """提取消息中的@提及"""
        pattern = r'@([^\s]+)'
        return re.findall(pattern, content)
    
    def extract_links(self, content: str) -> List[str]:
        """提取消息中的链接"""
        pattern = r'https?://[^\s]+'
        return re.findall(pattern, content)
    
    def format_forward_message(self, messages: List[Dict]) -> str:
        """格式化转发消息"""
        if not messages:
            return ""
        
        formatted = []
        for msg in messages:
            time_str = datetime.fromtimestamp(msg.get('time', 0)).strftime('%H:%M:%S')
            sender = msg.get('sender_name', '未知')
            content = msg.get('content', '')
            formatted.append(f"[{time_str}] {sender}: {content}")
        
        return '\n'.join(formatted)