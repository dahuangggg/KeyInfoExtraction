import json
import sys
import os
import time
from pathlib import Path
import logging
import requests
from docx import Document

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# 或者直接添加backend目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm_extractor_v1 import LLMExtractor

def test_extract_single(file_path, format_json_path, output_dir='fixed_results'):
    """
    测试修复后的提取方法处理单个文件
    
    参数:
        file_path: 测试文档文件路径
        format_json_path: 格式定义JSON文件路径
        output_dir: 输出目录
    """
    print(f"开始测试修复后的提取方法（单个文件）: {file_path}")
    start_time = time.time()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化提取器
    extractor = LLMExtractor(
        format_json_path=format_json_path,
        terminology_file='./terminology.txt',
        server_ip='10.112.11.125',  # 根据实际情况修改
        server_port='11434',
        model_name='deepseek-r1:32b',
        debug=True
    )
    
    # 执行提取 - 使用统一方法
    results = extractor.extract(
        file_path_or_paths=file_path,
        output_dir=output_dir,
        output_json=True, 
        output_excel=True,
        batch=True,  # 启用批处理
        max_workers=4,
        batch_by_group=True
    )
    
    # 计算总处理时间
    total_time = time.time() - start_time
    
    # 输出结果摘要
    print(f"\n提取完成:")
    print(f"- 提取结果数: {len(results)}个")
    print(f"- 总处理时间: {total_time:.2f}秒")
    
    # 保存结果摘要
    summary = {
        "file_path": file_path,
        "processing": {
            "results_count": len(results),
            "total_time": total_time
        }
    }
    
    summary_file = os.path.join(output_dir, f"{Path(file_path).stem}_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"摘要已保存到: {summary_file}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python test_fixed.py <文档文件路径> <格式定义JSON路径> [输出目录]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    format_json_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'fixed_results'
    
    test_extract_single(file_path, format_json_path, output_dir) 