import os
import sys
import argparse
from doc_processor import DocProcessor
from extractors import LLMExtractor
from utils import save_json, filter_empty_values

class InformationExtractionSystem:
    """信息提取系统主类"""
    
    def __init__(self):
        self.doc_processor = DocProcessor()
        # 示例路径，实际应替换为真实模型路径
        # self.rule_extractor = InformationExtractor("./models/ner", "./models/relation")
        self.llm_extractor = LLMExtractor()
        
    def process_document(self, file_path):
        """处理单个文档"""
        # 解析文档
        text = self.doc_processor.parse_docx(file_path)
        
        # 分割章节
        sections = self.doc_processor.split_into_sections(text)
        
        # 提取信息
        results = {}
        for section_title, section_text in sections.items():
            print(f"处理章节: {section_title}")
            # 使用LLM提取信息
            section_info = self.llm_extractor.extract_info(section_text, section_title)
            results[section_title] = section_info
        
        return results
    
    def format_output(self, results):
        """格式化输出结果"""
        # 结构化信息
        structured_info = {
            "器件信息": {
                "型号": None,
                "批次": None,
                "生产厂": None
            },
            "封装信息": {},
            "芯片信息": {},
            "键合信息": {},
            "问题与建议": []
        }
        
        # 遍历所有章节，尝试提取有用信息
        for section, info in results.items():
            print(f"处理章节结果: {section}")
            # 如果是字典类型，尝试提取信息
            if isinstance(info, dict):
                # 提取问题与建议
                if "问题与建议" in info:
                    structured_info["问题与建议"].extend(info["问题与建议"])
                
                # 提取器件信息
                if "型号规格" in info:
                    structured_info["器件信息"]["型号"] = info["型号规格"]
                if "生产批次" in info:
                    structured_info["器件信息"]["批次"] = info["生产批次"]
                if "生产厂标识" in info:
                    structured_info["器件信息"]["生产厂"] = info["生产厂标识"]
                
                # 提取封装信息
                if "封装类型" in info or "封装材料" in info or "封装工艺" in info:
                    for key in ["封装类型", "封装材料", "封装工艺", "质量评估"]:
                        if key in info:
                            structured_info["封装信息"][key] = info[key]
                
                # 提取芯片信息
                if "芯片类型" in info or "芯片工艺" in info:
                    structured_info["芯片信息"]["芯片类型"] = info.get("芯片类型")
                    structured_info["芯片信息"]["芯片工艺"] = info.get("芯片工艺")
                
                # 提取键合信息
                if "键合方式" in info:
                    structured_info["键合信息"]["键合方式"] = info.get("键合方式")
                
                # 如果是模拟LLM提取结果，尝试从章节标题推断类型
                if "extracted_info" in info and info["extracted_info"] == "模拟LLM提取结果":
                    if "详细分析" in section:
                        # 假设详细分析包含了器件、封装、芯片和键合的信息
                        # 这里可以添加一些默认值或者从章节文本中提取信息
                        structured_info["器件信息"]["型号"] = "从详细分析中提取的型号"
                        structured_info["器件信息"]["批次"] = "从详细分析中提取的批次"
                        structured_info["器件信息"]["生产厂"] = "从详细分析中提取的生产厂"
                        structured_info["封装信息"] = {"封装类型": "从详细分析中提取的封装类型"}
                        structured_info["芯片信息"] = {"芯片类型": "从详细分析中提取的芯片类型"}
                        structured_info["键合信息"] = {"键合类型": "从详细分析中提取的键合类型"}
                        structured_info["问题与建议"].append("从详细分析中提取的建议")
        
        # 过滤空值
        return filter_empty_values(structured_info)
    
    def batch_process(self, directory_path, output_dir="./output"):
        """批量处理目录下的所有文档"""
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        results = {}
        for filename in os.listdir(directory_path):
            if filename.endswith(".docx") or filename.endswith(".doc") or filename.endswith(".txt"):
                file_path = os.path.join(directory_path, filename)
                print(f"处理文档: {filename}")
                result = self.process_document(file_path)
                formatted_result = self.format_output(result)
                results[filename] = formatted_result
                
                # 保存单个文件的结果
                output_file = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_output.json")
                save_json(formatted_result, output_file)
        
        # 保存批量处理的汇总结果
        save_json(results, os.path.join(output_dir, "batch_results.json"))
        return results


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="器件信息提取系统")
    parser.add_argument("--file", "-f", help="要处理的单个文件路径")
    parser.add_argument("--dir", "-d", help="要批量处理的目录路径")
    parser.add_argument("--output", "-o", default="./output", help="输出目录路径")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 初始化系统
    system = InformationExtractionSystem()
    
    if args.file:
        # 处理单个文件
        if not os.path.exists(args.file):
            print(f"文件不存在: {args.file}")
            return 1
        
        print(f"正在处理文件: {args.file}")
        result = system.process_document(args.file)
        
        # 调试输出
        print("提取结果:")
        for section, info in result.items():
            print(f"  {section}:")
            for key, value in info.items():
                print(f"    {key}: {value}")
        
        formatted_result = system.format_output(result)
        
        # 确保输出目录存在
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        
        # 保存结果
        output_file = os.path.join(args.output, f"{os.path.splitext(os.path.basename(args.file))[0]}_output.json")
        save_json(formatted_result, output_file)
        
        print(f"提取完成，结果已保存到 {output_file}")
        
    elif args.dir:
        # 批量处理目录
        if not os.path.exists(args.dir):
            print(f"目录不存在: {args.dir}")
            return 1
        
        print(f"正在批量处理目录: {args.dir}")
        results = system.batch_process(args.dir, args.output)
        print(f"批量处理完成，结果已保存到 {args.output}")
        
    else:
        # 如果没有指定文件或目录，使用默认测试文件
        test_file = "./test.docx"
        if not os.path.exists(test_file):
            print(f"测试文件不存在: {test_file}")
            return 1
        
        print(f"正在处理默认测试文件: {test_file}")
        result = system.process_document(test_file)
        
        # 调试输出
        print("提取结果:")
        for section, info in result.items():
            print(f"  {section}:")
            for key, value in info.items():
                print(f"    {key}: {value}")
        
        formatted_result = system.format_output(result)
        
        # 保存结果
        save_json(formatted_result, "output.json")
        
        print("提取完成，结果已保存到output.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())