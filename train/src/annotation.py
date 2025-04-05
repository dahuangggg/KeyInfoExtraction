import os
import re
import json
import argparse
from tqdm import tqdm
import numpy as np

def create_annotation_tool(documents, knowledge_base, output_dir=None):
    """
    自动标注并生成标注文件
    
    Args:
        documents: 文档列表
        knowledge_base: 知识库
        output_dir: 输出目录
    
    Returns:
        标注后的文档列表
    """
    annotated_docs = []
    
    for doc in tqdm(documents, desc="Annotating documents"):
        text = doc['text']
        annotations = []
        
        # 基于知识库进行初步自动标注
        # 物理状态组标注
        for entity in knowledge_base['PhyGroup']:
            for match in re.finditer(re.escape(entity), text):
                start, end = match.span()
                annotations.append({
                    'start': start,
                    'end': end,
                    'text': text[start:end],
                    'type': 'PhyGroup'
                })
        
        # 物理状态标注
        for entity in knowledge_base['PhyState']:
            for match in re.finditer(re.escape(entity), text):
                start, end = match.span()
                # 检查是否已被标注
                overlap = False
                for ann in annotations:
                    if start < ann['end'] and end > ann['start']:
                        overlap = True
                        break
                
                if not overlap:
                    annotations.append({
                        'start': start,
                        'end': end,
                        'text': text[start:end],
                        'type': 'PhyState'
                    })
        
        # 试验项目标注
        for entity in knowledge_base['TestItem']:
            for match in re.finditer(re.escape(entity), text):
                start, end = match.span()
                # 检查是否已被标注
                overlap = False
                for ann in annotations:
                    if start < ann['end'] and end > ann['start']:
                        overlap = True
                        break
                
                if not overlap:
                    annotations.append({
                        'start': start,
                        'end': end,
                        'text': text[start:end],
                        'type': 'TestItem'
                    })
        
        # 将标注结果保存
        annotated_doc = doc.copy()
        annotated_doc['annotations'] = annotations
        annotated_docs.append(annotated_doc)
        
        # 输出标注文件
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{os.path.splitext(doc['file_name'])[0]}_annotated.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(annotated_doc, f, ensure_ascii=False, indent=2)
    
    return annotated_docs

def convert_to_training_data(annotated_docs, output_dir=None):
    """
    将标注文档转换为训练数据
    
    Args:
        annotated_docs: 标注后的文档列表
        output_dir: 输出目录
    
    Returns:
        训练数据列表
    """
    training_data = []
    
    for doc in tqdm(annotated_docs, desc="Converting to training data"):
        text = doc['text']
        annotations = doc['annotations']
        
        # 按字符位置排序标注
        annotations.sort(key=lambda x: x['start'])
        
        # 转换为字符级BIOES标注
        char_labels = ['O'] * len(text)
        
        for ann in annotations:
            start, end = ann['start'], ann['end']
            entity_type = ann['type']
            entity_len = end - start
            
            if entity_len == 1:  # 单字实体
                char_labels[start] = f'S-{entity_type}'
            else:  # 多字实体
                char_labels[start] = f'B-{entity_type}'
                for i in range(start + 1, end - 1):
                    char_labels[i] = f'I-{entity_type}'
                char_labels[end - 1] = f'E-{entity_type}'
        
        # 分段处理长文档
        max_len = 510  # BERT最大长度-2(CLS和SEP标记)
        stride = max_len // 2  # 滑动窗口步长
        
        for i in range(0, len(text), stride):
            segment_text = text[i:i+max_len]
            segment_labels = char_labels[i:i+max_len]
            
            if len(segment_text.strip()) > 0:  # 确保段落不为空
                segment_data = {
                    'text': segment_text,
                    'labels': segment_labels,
                    'file_name': doc['file_name'],
                    'start_pos': i
                }
                training_data.append(segment_data)
        
        # 输出训练数据
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{os.path.splitext(doc['file_name'])[0]}_training.json")
            
            # 保存为JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    return training_data

def convert_to_hierarchical_format(training_data, output_dir=None):
    """
    将标准训练数据转换为层次格式
    
    Args:
        training_data: 标准训练数据
        output_dir: 输出目录
    
    Returns:
        层次格式的训练数据
    """
    hierarchical_data = []
    
    for item in tqdm(training_data, desc="Converting to hierarchical format"):
        text = item['text']
        labels = item['labels']
        
        # 分离一级标签（物理状态组）和二级标签（物理状态、试验项目）
        level1_labels = []
        level2_labels = []
        
        for label in labels:
            if label.endswith('-PhyGroup'):
                level1_labels.append(label)
                level2_labels.append('O')
            elif label.endswith('-PhyState') or label.endswith('-TestItem'):
                level1_labels.append('O')
                level2_labels.append(label)
            else:
                level1_labels.append('O')
                level2_labels.append('O')
        
        hierarchical_item = {
            'text': text,
            'level1_labels': level1_labels,
            'level2_labels': level2_labels,
            'file_name': item.get('file_name', ''),
            'start_pos': item.get('start_pos', 0)
        }
        
        hierarchical_data.append(hierarchical_item)
    
    # 输出层次格式的训练数据
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "hierarchical_training_data.json")
        
        # 保存为JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(hierarchical_data, f, ensure_ascii=False, indent=2)
    
    return hierarchical_data

def manual_annotation_correction(annotation_file, output_file):
    """
    手动修正自动标注结果的辅助工具
    
    Args:
        annotation_file: 自动标注文件路径
        output_file: 修正后的输出文件路径
    """
    with open(annotation_file, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    
    text = doc['text']
    annotations = doc['annotations']
    
    print("Manual Annotation Correction Tool")
    print("=================================")
    print(f"Document: {doc['file_name']}")
    print(f"Total annotations: {len(annotations)}")
    print("Commands: 'a' to add, 'd' to delete, 'm' to modify, 's' to save, 'q' to quit")
    print("=================================")
    
    # 显示当前标注
    def show_annotations():
        print("\nCurrent Annotations:")
        for i, ann in enumerate(annotations):
            print(f"{i}. [{ann['start']}:{ann['end']}] {ann['text']} ({ann['type']})")
    
    show_annotations()
    
    while True:
        cmd = input("\nEnter command (a/d/m/s/q): ").strip().lower()
        
        if cmd == 'q':
            if input("Save before quitting? (y/n): ").strip().lower() == 'y':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                print(f"Saved to {output_file}")
            break
        
        elif cmd == 's':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print(f"Saved to {output_file}")
        
        elif cmd == 'a':
            # 添加新标注
            start = int(input("Enter start position: "))
            end = int(input("Enter end position: "))
            entity_text = text[start:end]
            print(f"Selected text: '{entity_text}'")
            entity_type = input("Enter entity type (PhyGroup/PhyState/TestItem): ")
            
            annotations.append({
                'start': start,
                'end': end,
                'text': entity_text,
                'type': entity_type
            })
            
            # 排序标注
            annotations.sort(key=lambda x: x['start'])
            show_annotations()
        
        elif cmd == 'd':
            # 删除标注
            idx = int(input("Enter annotation index to delete: "))
            if 0 <= idx < len(annotations):
                del annotations[idx]
                show_annotations()
            else:
                print("Invalid index")
        
        elif cmd == 'm':
            # 修改标注
            idx = int(input("Enter annotation index to modify: "))
            if 0 <= idx < len(annotations):
                ann = annotations[idx]
                print(f"Current: [{ann['start']}:{ann['end']}] {ann['text']} ({ann['type']})")
                
                start = input(f"Enter new start position (current: {ann['start']}): ")
                end = input(f"Enter new end position (current: {ann['end']}): ")
                entity_type = input(f"Enter new entity type (current: {ann['type']}): ")
                
                if start.strip():
                    ann['start'] = int(start)
                if end.strip():
                    ann['end'] = int(end)
                if entity_type.strip():
                    ann['type'] = entity_type
                
                # 更新文本
                ann['text'] = text[ann['start']:ann['end']]
                
                # 排序标注
                annotations.sort(key=lambda x: x['start'])
                show_annotations()
            else:
                print("Invalid index")
        
        else:
            print("Unknown command")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据标注工具")
    parser.add_argument("--data_dir", type=str, required=True, help="预处理文档目录")
    parser.add_argument("--knowledge_base", type=str, required=True, help="知识库文件路径")
    parser.add_argument("--output_dir", type=str, required=True, help="标注输出目录")
    parser.add_argument("--training_dir", type=str, help="训练数据输出目录")
    parser.add_argument("--hierarchical", action="store_true", help="是否转换为层次格式")
    
    args = parser.parse_args()
    
    # 加载预处理文档
    documents = []
    for file in os.listdir(args.data_dir):
        if file.endswith('_preprocessed.json'):
            with open(os.path.join(args.data_dir, file), 'r', encoding='utf-8') as f:
                documents.append(json.load(f))
    
    # 加载知识库
    with open(args.knowledge_base, 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    
    # 自动标注
    annotated_docs = create_annotation_tool(documents, knowledge_base, args.output_dir)
    
    # 转换为训练数据
    if args.training_dir:
        training_data = convert_to_training_data(annotated_docs, args.training_dir)
        
        # 转换为层次格式
        if args.hierarchical:
            hierarchical_data = convert_to_hierarchical_format(training_data, args.training_dir)
            print(f"生成了{len(hierarchical_data)}条层次格式的训练数据")
        
        print(f"生成了{len(training_data)}条训练数据")
    
    print(f"标注了{len(annotated_docs)}份文档")

if __name__ == "__main__":
    main()