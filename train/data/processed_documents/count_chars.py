import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def visualize_char_counts(char_counts):
    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot histogram
    ax1.hist(char_counts, bins=20, edgecolor='black')
    ax1.set_title('Distribution of Document Character Counts')
    ax1.set_xlabel('Number of Characters')
    ax1.set_ylabel('Number of Documents')
    
    # Add mean and median lines
    mean_chars = np.mean(char_counts)
    median_chars = np.median(char_counts)
    ax1.axvline(mean_chars, color='red', linestyle='dashed', linewidth=1, label=f'Mean: {mean_chars:.0f}')
    ax1.axvline(median_chars, color='green', linestyle='dashed', linewidth=1, label=f'Median: {median_chars:.0f}')
    ax1.legend()
    
    # Plot box plot
    ax2.boxplot(char_counts, vert=False)
    ax2.set_title('Box Plot of Document Character Counts')
    ax2.set_xlabel('Number of Characters')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('char_count_visualization.png', dpi=300, bbox_inches='tight')
    print("\n可视化结果已保存为 'char_count_visualization.png'")
    print("图表说明：")
    print("1. 上方直方图显示了文档字符数的分布情况")
    print("   - 红色虚线表示平均值")
    print("   - 绿色虚线表示中位数")
    print("2. 下方箱线图显示了字符数的统计特征")
    print("   - 箱体表示25%到75%的数据范围")
    print("   - 箱体中的线表示中位数")
    print("   - 触须表示最小值和最大值（不包括异常值）")
    print("   - 单独的点表示异常值")

def count_chars_in_files():
    # 获取当前目录下的 data_txt 文件夹
    data_dir = Path(__file__).parent / 'data_txt'
    
    # 存储每个文件的字符数
    file_chars = {}
    total_chars = 0
    file_count = 0
    
    # 遍历所有 txt 文件
    for file_path in data_dir.glob('*.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                char_count = len(content)
                file_chars[file_path.name] = char_count
                total_chars += char_count
                file_count += 1
        except Exception as e:
            print(f"处理文件 {file_path.name} 时出错: {str(e)}")
    
    # 打印每个文件的字符数
    print("\n每个文件的字符数统计：")
    print("-" * 50)
    for filename, count in sorted(file_chars.items()):
        print(f"{filename}: {count} 字符")
    
    # 打印总体统计信息
    print("\n总体统计：")
    print("-" * 50)
    print(f"文件总数: {file_count}")
    print(f"总字符数: {total_chars}")
    if file_count > 0:
        print(f"平均字符数: {total_chars / file_count:.2f}")
        
        # 计算更多统计指标
        char_counts = list(file_chars.values())
        median = np.median(char_counts)
        std = np.std(char_counts)
        print(f"中位数: {median:.2f}")
        print(f"标准差: {std:.2f}")
        print(f"最小值: {min(char_counts)}")
        print(f"最大值: {max(char_counts)}")
        
        # 生成可视化
        visualize_char_counts(char_counts)

if __name__ == "__main__":
    count_chars_in_files() 