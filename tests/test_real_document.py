import os
import json
import argparse
from extractors.llm_extractor import LLMExtractor

def extract_from_file(file_path, api_key, model_name="gpt-3.5-turbo", section_type=None):
    """
    从文件中提取信息
    
    参数:
        file_path: 文本文件路径
        api_key: OpenAI API密钥
        model_name: 模型名称
        section_type: 章节类型，如果为None则自动检测
    """
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 初始化提取器
    extractor = LLMExtractor(
        model_name=model_name,
        use_api=True,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000
    )
    
    # 如果未指定章节类型，尝试自动检测
    if section_type is None:
        # 简单的章节类型检测逻辑
        if "标识" in text[:100]:
            section_type = "标识部分"
        elif "封装" in text[:100]:
            section_type = "封装结构"
        elif "芯片" in text[:100]:
            section_type = "芯片"
        elif "键合" in text[:100]:
            section_type = "键合系统"
        elif "详细分析" in text[:100]:
            section_type = "三、详细分析"
        elif "附图" in text[:100]:
            section_type = "四、附图"
        else:
            section_type = "未知章节"
    
    print(f"从文件 {file_path} 中提取 {section_type} 信息...")
    
    # 提取信息
    result = extractor.extract_info(text, section_type)
    
    # 打印结果
    print("\n提取结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 评分
    score_info = extractor.score_extraction_result(result, text)
    print("\n评分结果:")
    print(json.dumps(score_info, ensure_ascii=False, indent=2))
    
    # 保存结果到JSON文件
    output_file = os.path.splitext(file_path)[0] + "_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    
    return result

def extract_from_directory(dir_path, api_key, model_name="gpt-3.5-turbo", file_ext=".txt"):
    """
    从目录中的所有文件提取信息
    
    参数:
        dir_path: 目录路径
        api_key: OpenAI API密钥
        model_name: 模型名称
        file_ext: 文件扩展名
    """
    # 获取目录中的所有文件
    files = [f for f in os.listdir(dir_path) if f.endswith(file_ext)]
    
    if not files:
        print(f"目录 {dir_path} 中没有找到 {file_ext} 文件")
        return
    
    print(f"在目录 {dir_path} 中找到 {len(files)} 个{file_ext}文件")
    
    # 处理每个文件
    for file in files:
        file_path = os.path.join(dir_path, file)
        print(f"\n处理文件: {file}")
        extract_from_file(file_path, api_key, model_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用LLM从文档中提取信息")
    parser.add_argument("--file", help="要处理的文本文件路径")
    parser.add_argument("--dir", help="要处理的目录路径")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="要使用的模型名称")
    parser.add_argument("--section", help="章节类型")
    parser.add_argument("--api_key", help="OpenAI API密钥")
    
    args = parser.parse_args()
    
    # 获取API密钥
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = input("请输入您的OpenAI API密钥: ")
    
    # 处理文件或目录
    if args.file:
        extract_from_file(args.file, api_key, args.model, args.section)
    elif args.dir:
        extract_from_directory(args.dir, api_key, args.model)
    else:
        print("请指定要处理的文件(--file)或目录(--dir)")
        parser.print_help() 