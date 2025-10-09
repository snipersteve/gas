import json
import os
from typing import List, Set
from config import USER_DATA_FILE

class UserManager:
    def __init__(self):
        self.data_file = USER_DATA_FILE
        self.users_data = self.load_data()
    
    def load_data(self) -> dict:
        """从文件加载用户数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading user data: {e}")
                return {}
        return {}
    
    def save_data(self):
        """保存用户数据到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving user data: {e}")
    
    def add_address(self, user_id: int, address: str) -> bool:
        """为用户添加监控地址"""
        user_id_str = str(user_id)
        address = address.lower()
        
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {
                'addresses': [],
                'last_alert': {}
            }
        
        addresses = self.users_data[user_id_str]['addresses']
        
        if address not in addresses:
            addresses.append(address)
            self.save_data()
            return True
        return False
    
    def remove_address(self, user_id: int, address: str) -> bool:
        """移除用户的监控地址"""
        user_id_str = str(user_id)
        address = address.lower()
        
        if user_id_str in self.users_data:
            addresses = self.users_data[user_id_str]['addresses']
            if address in addresses:
                addresses.remove(address)
                # 同时移除该地址的警告记录
                if address in self.users_data[user_id_str]['last_alert']:
                    del self.users_data[user_id_str]['last_alert'][address]
                self.save_data()
                return True
        return False
    
    def get_addresses(self, user_id: int) -> List[str]:
        """获取用户的监控地址列表"""
        user_id_str = str(user_id)
        if user_id_str in self.users_data:
            return self.users_data[user_id_str]['addresses'].copy()
        return []
    
    def get_all_users(self) -> List[int]:
        """获取所有用户ID"""
        return [int(user_id) for user_id in self.users_data.keys()]
    
    def get_all_addresses(self) -> Set[str]:
        """获取所有被监控的地址"""
        all_addresses = set()
        for user_data in self.users_data.values():
            all_addresses.update(user_data['addresses'])
        return all_addresses
    
    def should_send_alert(self, user_id: int, address: str, current_time: float) -> bool:
        """检查是否应该发送警告（避免重复发送）"""
        user_id_str = str(user_id)
        address = address.lower()
        
        if user_id_str not in self.users_data:
            return True
        
        last_alert_time = self.users_data[user_id_str]['last_alert'].get(address, 0)
        # 24小时内不重复发送同一地址的警告
        return current_time - last_alert_time > 24 * 3600
    
    def record_alert(self, user_id: int, address: str, current_time: float):
        """记录警告发送时间"""
        user_id_str = str(user_id)
        address = address.lower()
        
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {
                'addresses': [],
                'last_alert': {}
            }
        
        self.users_data[user_id_str]['last_alert'][address] = current_time
        self.save_data()
    
    def get_user_addresses_mapping(self) -> dict:
        """获取地址到用户的映射"""
        address_to_users = {}
        for user_id_str, user_data in self.users_data.items():
            user_id = int(user_id_str)
            for address in user_data['addresses']:
                if address not in address_to_users:
                    address_to_users[address] = []
                address_to_users[address].append(user_id)
        return address_to_users