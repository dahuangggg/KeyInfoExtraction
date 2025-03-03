import os
import sys
import argparse
from doc_processor import DocProcessor
from extractors import LLMExtractor
from extractors.rule_extractor import InformationExtractor
from utils import save_json, save_excel, filter_empty_values

class InformationExtractionSystem:
    """信息提取系统主类"""
    
    def __init__(self, use_custom_models=False, ner_model_path="models/ner", relation_model_path="models/relation"):
        """
        初始化信息提取系统
        
        参数:
            use_custom_models: 是否使用自定义训练的模型
            ner_model_path: NER模型路径
            relation_model_path: 关系抽取模型路径
        """
        self.doc_processor = DocProcessor()
        self.use_custom_models = use_custom_models
        
        # 根据配置选择使用的提取器
        if use_custom_models:
            print(f"使用自定义训练的模型: NER={ner_model_path}, Relation={relation_model_path}")
            self.rule_extractor = InformationExtractor(
                ner_model_path=ner_model_path,
                relation_model_path=relation_model_path,
                use_models=True
            )
            self.extractor = self.rule_extractor
        else:
            print("使用LLM提取器")
            self.llm_extractor = LLMExtractor()
            self.extractor = self.llm_extractor
        
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
            # 使用选定的提取器提取信息
            section_info = self.extractor.extract_info(section_text, section_title)
            results[section_title] = section_info
        
        return results
    
    def format_output(self, results):
        """格式化输出结果"""
        # 初始化结构化信息
        structured_info = {
            "元器件物理状态分析": []
        }
        
        # 遍历所有章节
        for section_title, section_info in results.items():
            # 跳过附图和附表章节
            if "附图" in section_title or "附表" in section_title:
                print(f"跳过章节: {section_title}")
                continue
                
            # 检查是否存在物理状态组信息
            if "物理状态组" in section_info:
                # 将物理状态组信息添加到结构化信息中
                physical_state_group = {
                    "物理状态组": section_title,
                    "物理状态项": []
                }
                
                for state in section_info["物理状态组"]:
                    physical_state_item = {
                        "物理状态名称": state.get("物理状态名称", ""),
                        "典型物理状态值": state.get("典型物理状态值", ""),
                        "禁限用信息": state.get("禁限用信息", "无"),
                        "测试评语": state.get("测试评语", "")
                    }
                    physical_state_group["物理状态项"].append(physical_state_item)
                
                structured_info["元器件物理状态分析"].append(physical_state_group)
            else:
                # 尝试处理旧格式
                print(f"警告: 章节 {section_title} 的数据格式不符合预期，尝试转换...")
                
                # 尝试从旧格式转换
                physical_state_items = []
                
                # 遍历章节信息中的所有键
                for key, value in section_info.items():
                    # 跳过非字典类型的值
                    if not isinstance(value, dict):
                        continue
                    
                    # 构建物理状态
                    physical_state_item = {
                        "物理状态名称": key,
                        "典型物理状态值": value.get("值", "文中未提及"),
                        "禁限用信息": value.get("禁限用信息", "无"),
                        "测试评语": value.get("测试评语", "文中未提及")
                    }
                    
                    physical_state_items.append(physical_state_item)
                
                # 添加到结构化信息
                if physical_state_items:
                    physical_state_group = {
                        "物理状态组": section_title,
                        "物理状态项": physical_state_items
                    }
                    structured_info["元器件物理状态分析"].append(physical_state_group)
                else:
                    print(f"警告: 无法从章节 {section_title} 提取物理状态信息")
        
        return structured_info
    
    def batch_process(self, directory_path, output_dir="./output", use_custom_models=False, output_format="json"):
        """批量处理目录中的文档"""
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取目录中的所有docx文件
        docx_files = []
        for file in os.listdir(directory_path):
            if file.endswith(".docx") and not file.startswith("~$"):
                docx_files.append(os.path.join(directory_path, file))
        
        print(f"找到 {len(docx_files)} 个docx文件")
        
        # 处理每个文件
        for file_path in docx_files:
            file_name = os.path.basename(file_path)
            print(f"处理文件: {file_name}")
            
            try:
                # 处理文档
                results = self.process_document(file_path)
                
                # 格式化输出
                structured_info = self.format_output(results)
                
                # 保存结果
                base_output_file = os.path.join(output_dir, os.path.splitext(file_name)[0])
                
                # 根据指定格式保存
                if output_format in ["json", "both"]:
                    json_output_file = base_output_file + ".json"
                    save_json(structured_info, json_output_file)
                
                if output_format in ["excel", "both"]:
                    excel_output_file = base_output_file + ".xlsx"
                    save_excel(structured_info, excel_output_file)
                
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
        
        print("批处理完成")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="信息提取系统")
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", help="要处理的文件路径")
    input_group.add_argument("--dir", help="要处理的目录路径")
    
    # 输出参数
    parser.add_argument("--output", default="./output", help="输出目录")
    parser.add_argument("--format", choices=["json", "excel", "both"], default="json", 
                        help="输出格式: json, excel 或 both (同时输出两种格式)")
    
    # 模型参数
    parser.add_argument("--use_custom_models", action="store_true", help="使用自定义模型")
    parser.add_argument("--ner_model", default="./models/ner", help="NER模型路径")
    parser.add_argument("--relation_model", default="./models/relation", help="关系抽取模型路径")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 初始化系统
    system = InformationExtractionSystem(
        use_custom_models=args.use_custom_models,
        ner_model_path=args.ner_model,
        relation_model_path=args.relation_model
    )
    
    # 处理单个文件或目录
    if args.file:
        print(f"处理文件: {args.file}")
        results = system.process_document(args.file)
        structured_info = system.format_output(results)
        
        # 保存结果
        os.makedirs(args.output, exist_ok=True)
        base_output_file = os.path.join(args.output, os.path.splitext(os.path.basename(args.file))[0])
        
        # 根据指定格式保存
        if args.format in ["json", "both"]:
            json_output_file = base_output_file + ".json"
            save_json(structured_info, json_output_file)
        
        if args.format in ["excel", "both"]:
            excel_output_file = base_output_file + ".xlsx"
            save_excel(structured_info, excel_output_file)
            
    elif args.dir:
        print(f"批量处理目录: {args.dir}")
        # 修改batch_process方法调用，传入输出格式参数
        system.batch_process(args.dir, args.output, args.use_custom_models, output_format=args.format)
    else:
        print("错误: 请指定要处理的文件或目录")
        sys.exit(1)

if __name__ == "__main__":
    main()