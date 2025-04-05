#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新版LLMExtractor测试脚本
用于测试改进后的LLMExtractor功能，支持直接处理文档文件
"""

import os
import sys
import json
import argparse
from pathlib import Path
from docx import Document
import pandas as pd

# 导入LLMExtractor
sys.path.append(os.getcwd())
from app.extractors.llm_extractor import LLMExtractor
from app.core.config import settings

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="测试新版LLMExtractor功能")
    parser.add_argument("--file", "-f", help="要处理的文档文件路径", required=True)
    parser.add_argument("--output", "-o", help="输出目录路径", default="./output")
    parser.add_argument("--format", choices=["json", "excel", "both"], default="both", 
                      help="输出格式: json, excel, both")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--server_ip", default="10.112.11.125", help="LLM服务器IP")
    parser.add_argument("--server_port", type=int, default=11434, help="LLM服务器端口")
    parser.add_argument("--model_name", default="deepseek-r1:32b", help="LLM模型名称")
    parser.add_argument("--api_key", default=settings.LLM_API_KEY, help="LLM API密钥")
    parser.add_argument("--show_text", action="store_true", help="显示文档文本内容")
    parser.add_argument("--use_local_api", action="store_true", help="使用本地API而不是云API")
    return parser.parse_args()

def save_to_excel(data, output_file):
    """将数据保存为Excel文件"""
    # 创建一个空的DataFrame列表
    dfs = []
    
    # 对每个物理状态组创建一个DataFrame
    for group_name, states in data.items():
        rows = []
        for state_name, state_info in states.items():
            row = {
                "物理状态名称": state_name,
                "物理状态值": state_info.get("值", ""),
                "禁限用信息": state_info.get("禁限用信息", ""),
                "测试评语": state_info.get("测试评语", "")
            }
            rows.append(row)
        
        if rows:
            df = pd.DataFrame(rows)
            # 添加一个空行和标题行
            title_df = pd.DataFrame([{"物理状态名称": f"物理状态组: {group_name}"}])
            dfs.append(title_df)
            dfs.append(df)
            dfs.append(pd.DataFrame())  # 空行
    
    # 如果有数据，则保存
    if dfs:
        # 创建一个ExcelWriter对象
        with pd.ExcelWriter(output_file) as writer:
            # 合并所有DataFrame并写入
            pd.concat(dfs).to_excel(writer, index=False, sheet_name="提取结果")
            
        print(f"Excel已保存到: {output_file}")
    else:
        print("没有数据可保存到Excel")

def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查文件是否存在
    file_path = args.file
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取文档文本内容
    try:
        doc = Document(file_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        
        if args.show_text:
            print("\n文档内容:")
            print("-" * 50)
            print(text[:5000] + "..." if len(text) > 5000 else text)
            print("-" * 50)
    except Exception as e:
        print(f"读取文档时出错: {e}")
        sys.exit(1)
    
    # 初始化LLMExtractor
    try:
        print("初始化LLMExtractor...")
        format_json_path = os.path.join("backend", "data_static", "format.json")
        terminology_file = os.path.join("backend", "data_static", "terminology.txt")
        
        # 创建提取器
        extractor = LLMExtractor(
            format_json_path=format_json_path,
            terminology_file=terminology_file,
            server_ip=args.server_ip,
            server_port=args.server_port,
            model_name=args.model_name,
            api_key=None if args.use_local_api else args.api_key,
            debug=args.debug
        )
        
        print(f"开始处理文件: {file_path}")
        
        # 提取信息
        results = extractor.extract(
            file_path_or_paths=file_path,
            output_dir=output_dir,
            output_json=args.format in ["json", "both"],
            output_excel=args.format in ["excel", "both"]
        )
        
        # 显示结果
        if results:
            print("\n提取结果摘要:")
            for group_name, states in results.items():
                print(f"物理状态组: {group_name}")
                print(f"  包含 {len(states)} 个物理状态")
                
                # 显示每个物理状态的详细信息
                if args.debug:
                    for state_name, state_info in states.items():
                        print(f"    - {state_name}:")
                        for key, value in state_info.items():
                            print(f"      {key}: {value}")
            
            # 保存结果
            base_name = os.path.basename(file_path)
            base_output = os.path.join(output_dir, os.path.splitext(base_name)[0])
            
            # 保存为JSON
            if args.format in ["json", "both"]:
                json_output_file = f"{base_output}_extracted.json"
                with open(json_output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"\nJSON结果已保存到: {json_output_file}")
            
            # 保存为Excel
            if args.format in ["excel", "both"]:
                excel_output_file = f"{base_output}_extracted.xlsx"
                save_to_excel(results, excel_output_file)
        else:
            print("未提取到任何结果")
            
    except Exception as e:
        print(f"提取信息时出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 