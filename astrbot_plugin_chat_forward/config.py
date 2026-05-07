import json
import os
from typing import Dict, Any, List
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_path = Path("data/plugins/chat_forward/config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "admins": [],  # 普通管理员列表
            "super_users": [],  # 超级管理员（可以添加/删除管理员）
            "max_forward_count": 100,  # 最大转发消息数量
            "enable_emoji": True,  # 是否启用表情包转发
            "forward_delay": 0.5  # 转发延迟（秒）
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)