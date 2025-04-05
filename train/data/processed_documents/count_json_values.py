import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import os
import matplotlib
from matplotlib.font_manager import FontProperties

# 设置中文字体
# 尝试多种常见的中文字体，macOS常用的中文字体
try:
    # macOS中文字体
    font_list = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'Microsoft YaHei', 'SimHei']
    font_found = False
    
    for font in font_list:
        try:
            # 测试字体是否可用
            font_prop = FontProperties(fname=matplotlib.font_manager.findfont(font))
            if font_prop:
                matplotlib.rcParams['font.family'] = font
                print(f"使用字体: {font}")
                font_found = True
                break
        except:
            continue
    
    if not font_found:
        # 如果找不到特定字体，尝试使用系统默认字体
        matplotlib.rcParams['font.sans-serif'] = ['sans-serif']
        # 解决负号显示问题
        matplotlib.rcParams['axes.unicode_minus'] = False
        print("使用系统默认字体")
except:
    print("设置字体失败，使用默认字体")

def analyze_json_labels(json_file_path):
    """
    分析JSON文件中六个标签的不同值数量并进行可视化
    """
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 六个标签
    labels = ['物理状态组', '物理状态', '试验项目', '物理状态值', '风险评价', '详细分析']
    
    # 统计每个标签下不同值的数量
    label_stats = {}
    label_values = {}
    
    for label in labels:
        # 提取当前标签的所有值
        values = [item[label] for item in data if label in item]
        # 统计不同值及其出现次数
        value_counts = Counter(values)
        # 保存统计结果
        label_stats[label] = len(value_counts)
        label_values[label] = value_counts
    
    # 打印统计结果
    print("\n标签值统计结果：")
    print("-" * 50)
    for label, count in label_stats.items():
        print(f"{label}: {count} 个不同值")
    
    # 详细输出每个标签的值及其出现频率
    for label, value_counts in label_values.items():
        print(f"\n{label} 的所有不同值及其频率：")
        print("-" * 50)
        for value, count in sorted(value_counts.items(), key=lambda x: x[1], reverse=True):
            # 如果是详细分析，内容可能很长，只显示前50个字符
            if label == '详细分析':
                display_value = value[:50] + "..." if len(value) > 50 else value
            else:
                display_value = value
            print(f"{display_value}: {count}次")
    
    # 可视化每个标签不同值的数量
    visualize_label_counts(label_stats)
    
    # 为每个标签创建前10个最常见值的饼图
    for label, value_counts in label_values.items():
        visualize_label_values(label, value_counts)

def visualize_label_counts(label_stats):
    """
    可视化每个标签不同值的数量
    """
    labels = list(label_stats.keys())
    counts = list(label_stats.values())
    
    # 生成英文标签用于显示
    english_labels = ['Physical State Group', 'Physical State', 'Test Item', 'Physical State Value', 'Risk Assessment', 'Detailed Analysis']
    label_mapping = dict(zip(labels, english_labels))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(english_labels, counts, color='skyblue')
    
    # 在每个柱状图上方显示数值
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 str(count), ha='center', va='bottom')
    
    plt.title('Number of Different Values for Each Label')
    plt.xlabel('Label Name')
    plt.ylabel('Count of Different Values')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('label_counts.png', dpi=300, bbox_inches='tight')
    print("\n各标签不同值的数量可视化结果已保存为 'label_counts.png'")

def visualize_label_values(label, value_counts):
    """
    可视化每个标签前10个最常见值的分布（饼图）
    """
    # 获取前10个最常见的值
    top_values = dict(sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # 如果值超过10个，其余的归为"其他"类别
    if len(value_counts) > 10:
        other_count = sum(count for value, count in value_counts.items() if value not in top_values)
        if other_count > 0:
            top_values['Others'] = other_count
    
    values = list(top_values.keys())
    counts = list(top_values.values())
    
    # 创建饼图 - 使用简化的英文标签或者数字标签
    plt.figure(figsize=(12, 8))
    
    # 设置labels为空，因为中文可能无法正确显示
    wedges, texts, autotexts = plt.pie(counts, labels=None, autopct='%1.1f%%', 
                              shadow=True, startangle=90)
    
    # 使用图例代替直接在饼图上的标签
    if len(values) <= 10:
        # 简化显示，只显示值的前10个字符，避免中文显示问题
        legend_labels = [f"{i+1}: {str(v)[:min(10, len(str(v)))]}" for i, v in enumerate(values)]
        plt.legend(wedges, legend_labels, title="Legend", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    plt.axis('equal')  # 保证饼图是圆形的
    
    # 使用英文标题
    english_title = {'物理状态组': 'Physical State Group', 
                    '物理状态': 'Physical State', 
                    '试验项目': 'Test Item', 
                    '物理状态值': 'Physical State Value', 
                    '风险评价': 'Risk Assessment', 
                    '详细分析': 'Detailed Analysis'}
    
    plt.title(f'Value Distribution for {english_title.get(label, label)} (Top 10 Most Common Values)')
    plt.tight_layout()
    plt.savefig(f'{label}_distribution.png', dpi=300, bbox_inches='tight')
    print(f"{label} 的值分布可视化结果已保存为 '{label}_distribution.png'")

if __name__ == "__main__":
    # 找到JSON文件路径（相对于当前文件的路径）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 向上一级找到知识库目录
    parent_dir = os.path.dirname(current_dir)
    json_file_path = os.path.join(parent_dir, 'knowledge_base', 'format.json')
    
    # 检查文件是否存在
    if os.path.exists(json_file_path):
        analyze_json_labels(json_file_path)
    else:
        print(f"错误：文件 {json_file_path} 不存在。")
        # 尝试查找格式相似的文件
        for root, dirs, files in os.walk(parent_dir):
            for file in files:
                if file.endswith('.json'):
                    full_path = os.path.join(root, file)
                    print(f"找到JSON文件：{full_path}") 