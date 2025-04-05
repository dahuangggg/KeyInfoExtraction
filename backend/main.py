import os
import sys
import argparse
import uvicorn
from app.services import InformationExtractionService
from app.extractors import LLMExtractor
from app.utils import save_json, save_excel
from app.core.config import settings

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="信息提取系统")
    
    # 服务器参数
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="是否启用热重载")
    
    # 命令行模式参数
    parser.add_argument("--cli", action="store_true", help="使用命令行模式而不是API服务器")
    parser.add_argument("--file", help="要处理的文件路径")
    parser.add_argument("--dir", help="要处理的目录路径")
    parser.add_argument("--output", default="./output", help="输出目录")
    parser.add_argument("--format", choices=["json", "excel", "both"], default="json", 
                        help="输出格式: json, excel 或 both (同时输出两种格式)")
    
    # LLM参数
    parser.add_argument("--server_ip", default=settings.LLM_SERVER_IP, help="LLM服务器IP")
    parser.add_argument("--server_port", type=int, default=int(settings.LLM_SERVER_PORT), help="LLM服务器端口")
    parser.add_argument("--model_name", default=settings.LLM_MODEL, help="LLM模型名称")
    parser.add_argument("--api_key", default=settings.LLM_API_KEY, help="LLM API密钥")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--use_local_api", action="store_true", help="使用本地API而不是云API")
    
    return parser.parse_args()

def cli_mode(args):
    """命令行模式"""
    # 配置LLM提取器所需的文件路径
    format_json_path = os.path.join("backend", "data_static", "format.json")
    terminology_file = os.path.join("backend", "data_static", "terminology.txt")
    
    print(f"使用格式定义文件: {format_json_path}")
    print(f"使用专有名词表: {terminology_file}")
    print(f"使用LLM模型: {args.model_name}")
    print(f"LLM服务器地址: {args.server_ip}:{args.server_port}")
    
    # 初始化提取器
    extractor = LLMExtractor(
        format_json_path=format_json_path,
        terminology_file=terminology_file,
        server_ip=args.server_ip,
        server_port=args.server_port,
        model_name=args.model_name,
        api_key=None if args.use_local_api else args.api_key,
        debug=args.debug
    )
    
    # 初始化服务
    service = InformationExtractionService(extractor=extractor)
    
    # 处理单个文件或目录
    if args.file:
        print(f"处理文件: {args.file}")
        results = service.process_document(args.file)
        structured_info = service.format_output(results)
        
        # 保存结果
        os.makedirs(args.output, exist_ok=True)
        base_output_file = os.path.join(args.output, os.path.splitext(os.path.basename(args.file))[0])
        
        # 根据指定格式保存
        if args.format in ["json", "both"]:
            json_output_file = base_output_file + ".json"
            save_json(structured_info, json_output_file)
            print(f"JSON结果已保存至: {json_output_file}")
        
        if args.format in ["excel", "both"]:
            excel_output_file = base_output_file + ".xlsx"
            save_excel(structured_info, excel_output_file)
            print(f"Excel结果已保存至: {excel_output_file}")
            
    elif args.dir:
        print(f"批量处理目录: {args.dir}")
        results = service.batch_process(args.dir, args.output, output_format=args.format)
        print(f"已处理 {len(results)} 个文件")
    else:
        print("错误: 请指定要处理的文件或目录")
        sys.exit(1)

def main():
    """主函数"""
    args = parse_args()
    
    if args.cli:
        # 命令行模式
        cli_mode(args)
    else:
        # API服务器模式
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload
        )

if __name__ == "__main__":
    main() 