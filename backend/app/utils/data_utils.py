from typing import Dict, List, Any

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
    """过滤掉字典中的空值"""
    if isinstance(data, dict):
        return {k: filter_empty_values(v) for k, v in data.items() if v not in [None, "", "文中未提及"]}
    elif isinstance(data, list):
        return [filter_empty_values(item) for item in data if item not in [None, "", "文中未提及"]]
    else:
        return data 