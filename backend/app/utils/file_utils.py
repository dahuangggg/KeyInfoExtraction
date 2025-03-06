import os
import json

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