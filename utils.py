import os
import json
import pandas as pd
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
    """过滤掉字典中的空值"""
    if isinstance(data, dict):
        return {k: filter_empty_values(v) for k, v in data.items() if v not in [None, "", "文中未提及"]}
    elif isinstance(data, list):
        return [filter_empty_values(item) for item in data if item not in [None, "", "文中未提及"]]
    else:
        return data

def save_excel(data, file_path):
    """
    将树状结构数据保存为Excel文件
    
    参数:
        data: 树状结构数据
        file_path: 输出Excel文件路径
    """
    # 创建一个Excel写入器
    writer = pd.ExcelWriter(file_path, engine='openpyxl')
    
    # 标记是否添加了任何工作表
    sheets_added = False
    
    # 处理树状结构数据
    if "元器件物理状态分析树状结构" in data:
        tree_data = data["元器件物理状态分析树状结构"]
        
        # 为每个章节创建一个工作表
        for section_title, section_data in tree_data.items():
            # 清理工作表名称（Excel工作表名称有限制）
            sheet_name = section_title[:31].replace('/', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('[', '_').replace(']', '_').replace(':', '_')
            
            # 提取物理状态组数据
            if "物理状态组" in section_data:
                physical_states = section_data["物理状态组"]
                
                # 将物理状态组转换为树状结构的行数据
                rows = []
                for state in physical_states:
                    # 获取物理状态名称和典型物理状态值
                    state_name = state.get("物理状态名称", "")
                    state_value = state.get("典型物理状态值", "")
                    prohibit_info = state.get("禁限用信息", "")
                    test_comment = state.get("测试评语", "")
                    
                    # 处理典型物理状态值可能是列表的情况
                    if isinstance(state_value, list):
                        # 如果是列表，为每个值创建一行
                        for i, value in enumerate(state_value):
                            if i == 0:
                                # 第一行包含物理状态名称
                                rows.append({
                                    "物理状态名称": state_name,
                                    "典型物理状态值": value,
                                    "禁限用信息": prohibit_info,
                                    "测试评语": test_comment
                                })
                            else:
                                # 后续行物理状态名称留空，表示属于同一个物理状态
                                rows.append({
                                    "物理状态名称": "",  # 留空表示与上一行同属一个物理状态
                                    "典型物理状态值": value,
                                    "禁限用信息": "",
                                    "测试评语": ""
                                })
                    else:
                        # 如果不是列表，直接添加一行
                        rows.append({
                            "物理状态名称": state_name,
                            "典型物理状态值": state_value,
                            "禁限用信息": prohibit_info,
                            "测试评语": test_comment
                        })
                
                # 创建DataFrame并保存到Excel工作表
                if rows:
                    df = pd.DataFrame(rows)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    sheets_added = True
                    
                    # 获取工作簿和工作表对象，用于设置格式
                    workbook = writer.book
                    worksheet = writer.sheets[sheet_name]
                    
                    # 合并相同物理状态名称的单元格
                    current_state_name = None
                    start_row = 1  # Excel行从1开始，但有标题行，所以数据从2开始
                    for i, row in enumerate(rows):
                        row_idx = i + 2  # 加2是因为有标题行和索引从1开始
                        
                        if row["物理状态名称"]:
                            # 如果有新的物理状态名称，处理之前的合并
                            if current_state_name and row_idx - start_row > 1:
                                # 合并单元格
                                cell_range = f"A{start_row}:A{row_idx-1}"
                                worksheet.merge_cells(cell_range)
                            
                            # 更新当前状态和起始行
                            current_state_name = row["物理状态名称"]
                            start_row = row_idx
                    
                    # 处理最后一组
                    if current_state_name and len(rows) + 2 - start_row > 1:
                        cell_range = f"A{start_row}:A{len(rows)+1}"
                        worksheet.merge_cells(cell_range)
    
    # 如果没有添加任何工作表，创建一个默认工作表
    if not sheets_added:
        # 尝试从数据中提取一些信息
        info_data = {}
        
        # 检查是否有器件信息
        if "器件信息" in data:
            for key, value in data["器件信息"].items():
                info_data[key] = [value]
        
        # 如果没有找到任何信息，添加一个空行
        if not info_data:
            info_data = {"信息": ["没有找到可用的树状结构数据"]}
        
        # 创建DataFrame并保存到默认工作表
        df = pd.DataFrame(info_data)
        df.to_excel(writer, sheet_name="基本信息", index=False)
    
    # 保存Excel文件
    writer.close()
    print(f"数据已保存到Excel文件: {file_path}")

def json_to_excel(json_file_path, excel_file_path=None):
    """
    将JSON文件转换为Excel文件
    
    参数:
        json_file_path: JSON文件路径
        excel_file_path: 输出Excel文件路径，如果为None则使用相同的文件名但扩展名为.xlsx
    """
    # 如果未指定Excel文件路径，则使用相同的文件名但扩展名为.xlsx
    if excel_file_path is None:
        excel_file_path = os.path.splitext(json_file_path)[0] + ".xlsx"
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 保存为Excel文件
    save_excel(data, excel_file_path)
    
    return excel_file_path

# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    import sys
    
    # 检查是否提供了JSON文件路径
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
        excel_file_path = json_to_excel(json_file_path)
        print(f"已将 {json_file_path} 转换为 {excel_file_path}")
    else:
        # 测试数据
        test_data = {
            "元器件物理状态分析树状结构": {
                "标识部分": {
                    "物理状态组": [
                        {
                            "物理状态名称": "器件型号",
                            "典型物理状态值": "XC9536",
                            "禁限用信息": "无",
                            "测试评语": "清晰可见"
                        },
                        {
                            "物理状态名称": "生产批次",
                            "典型物理状态值": "2023-A",
                            "禁限用信息": "无",
                            "测试评语": "标识完整"
                        }
                    ]
                },
                "封装结构": {
                    "物理状态组": [
                        {
                            "物理状态名称": "封装类型",
                            "典型物理状态值": "PLCC44",
                            "禁限用信息": "无",
                            "测试评语": "符合标准"
                        },
                        {
                            "物理状态名称": "封装材料",
                            "典型物理状态值": ["环氧树脂", "铜引线框架", "镀金层"],
                            "禁限用信息": "无",
                            "测试评语": "质量良好"
                        },
                        {
                            "物理状态名称": "引脚状态",
                            "典型物理状态值": ["完好", "无弯曲", "无氧化"],
                            "禁限用信息": "无",
                            "测试评语": "引脚状态良好"
                        }
                    ]
                }
            }
        }
        
        # 保存测试数据为JSON
        test_json_path = "test_tree_output.json"
        save_json(test_data, test_json_path)
        
        # 转换为Excel
        test_excel_path = json_to_excel(test_json_path)
        print(f"已创建测试Excel文件: {test_excel_path}") 