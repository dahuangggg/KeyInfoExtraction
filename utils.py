import os
import json
from typing import Dict, List, Any

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_json(data, file_path, ensure_ascii=False, indent=2):
    """保存数据为JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    print(f"数据已保存到: {file_path}")

def load_json(file_path):
    """从JSON文件加载数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件出错: {e}")
        return None

def merge_dicts(dict1, dict2):
    """合并两个字典，处理嵌套字典和列表"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result:
            # 如果两个值都是字典，递归合并
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            # 如果两个值都是列表，合并列表
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key].extend(value)
            # 否则，使用dict2的值覆盖dict1的值
            else:
                result[key] = value
        else:
            # 如果key不在result中，直接添加
            result[key] = value
    
    return result

def filter_empty_values(data):
    """过滤字典中的空值（None, [], {}, ''）"""
    if isinstance(data, dict):
        return {k: filter_empty_values(v) for k, v in data.items() 
                if v is not None and v != [] and v != {} and v != ''}
    elif isinstance(data, list):
        return [filter_empty_values(item) for item in data if item]
    else:
        return data 