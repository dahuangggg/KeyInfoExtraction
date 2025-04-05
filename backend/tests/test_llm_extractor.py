#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLMExtractor测试脚本
用于测试LLMExtractor的功能，不依赖FastAPI服务
"""

import os
import sys
import json
import argparse
from pathlib import Path
from app.extractors.llm_extractor import LLMExtractor
from app.core.config import settings

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="测试LLMExtractor功能")
    parser.add_argument("--file", "-f", help="要处理的文档文件路径", required=True)
    parser.add_argument("--output", "-o", help="输出目录路径", default="./output")
    parser.add_argument("--format", choices=["json", "excel", "both"], default="both", 
                      help="输出格式: json, excel, both")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--server_ip", default=settings.LLM_SERVER_IP, help="LLM服务器IP")
    parser.add_argument("--server_port", type=int, default=int(settings.LLM_SERVER_PORT), help="LLM服务器端口")
    parser.add_argument("--model_name", default=settings.LLM_MODEL, help="LLM模型名称")
    parser.add_argument("--api_key", default=settings.LLM_API_KEY, help="LLM API密钥")
    parser.add_argument("--use_local_api", action="store_true", help="使用本地API而不是云API")
    return parser.parse_args()

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
    
    # 初始化LLMExtractor
    format_json_path = os.path.join("backend", "data_static", "format.json")
    terminology_file = os.path.join("backend", "data_static", "terminology.txt")
    
    print(f"使用格式定义文件: {format_json_path}")
    print(f"使用专有名词表: {terminology_file}")
    print(f"使用LLM模型: {args.model_name}")
    print(f"LLM服务器地址: {args.server_ip}:{args.server_port}")
    
    try:
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
        output_json = args.format in ["json", "both"]
        output_excel = args.format in ["excel", "both"]
        
        results = extractor.extract(
            file_path_or_paths=file_path,
            output_dir=output_dir,
            output_json=output_json,
            output_excel=output_excel
        )
        
        # 显示结果
        print("\n提取结果摘要:")
        for group_name, states in results.items():
            print(f"物理状态组: {group_name}")
            print(f"  包含 {len(states)} 个物理状态")
        
        # 保存结果摘要
        summary_file = os.path.join(output_dir, "extraction_summary.json")
        summary = {
            "文件": os.path.basename(file_path),
            "物理状态组数量": len(results),
            "物理状态组": {group: len(states) for group, states in results.items()}
        }
        
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果摘要已保存到: {summary_file}")
        print("处理完成!")
        
    except Exception as e:
        print(f"错误: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 