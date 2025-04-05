#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import subprocess
import tempfile
import argparse
import re
from pathlib import Path
from tqdm import tqdm
import docx

def read_docx(file_path):
    """
    读取docx文件内容
    
    参数:
        file_path: docx文件路径
    
    返回:
        文档文本内容
    """
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def clean_text(text):
    """
    清洗文本，去除多余空格和特殊字符，但保留重要的标点和数值信息
    
    参数:
        text: 原始文本
    
    返回:
        清洗后的文本
    """
    # 去除多余空格，但保留单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 去除特殊字符，但保留需要的标点和数值相关字符
    # 保留中英文标点、数字、字母、单位符号
    text = re.sub(r'[^\w\s,.，。、；：""（）()μ%℃@\-\+\.g]', '', text)
    
    return text

def convert_doc_to_docx_with_libreoffice(doc_path, output_dir=None):
    """
    使用LibreOffice将doc文件转换为docx格式
    
    参数:
        doc_path: doc文件路径
        output_dir: 输出目录，默认为None（与原文件相同目录）
    
    返回:
        转换后的docx文件路径，如果转换失败则返回None
    """
    try:
        # 如果未指定输出目录，使用原文件所在目录
        if output_dir is None:
            output_dir = os.path.dirname(doc_path)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建输出文件路径
        file_name = os.path.basename(doc_path)
        docx_name = os.path.splitext(file_name)[0] + '.docx'
        output_path = os.path.join(output_dir, docx_name)
        
        # 检查LibreOffice路径
        libreoffice_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
            "soffice",  # 如果在PATH中
            "libreoffice",  # 某些Linux发行版
            r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows
        ]
        
        libreoffice_path = None
        for path in libreoffice_paths:
            if os.path.exists(path) or (path in ["soffice", "libreoffice"] and subprocess.call(["which", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0):
                libreoffice_path = path
                break
        
        if not libreoffice_path:
            print(f"错误: 未找到LibreOffice。请安装LibreOffice后再试。")
            return None
        
        # 执行转换命令
        cmd = [libreoffice_path, '--headless', '--convert-to', 'docx', '--outdir', output_dir, doc_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"转换失败: {stderr.decode('utf-8', errors='ignore')}")
            return None
        
        # 检查转换后的文件是否存在
        if os.path.exists(output_path):
            print(f"成功转换: {doc_path} -> {output_path}")
            return output_path
        else:
            print(f"转换后的文件不存在: {output_path}")
            return None
    
    except Exception as e:
        print(f"转换过程中出错: {e}")
        return None

def convert_doc_to_docx_with_word(doc_path, output_dir=None):
    """
    使用Microsoft Word将doc文件转换为docx格式
    
    参数:
        doc_path: doc文件路径
        output_dir: 输出目录，默认为None（与原文件相同目录）
    
    返回:
        转换后的docx文件路径，如果转换失败则返回None
    """
    try:
        # 如果未指定输出目录，使用原文件所在目录
        if output_dir is None:
            output_dir = os.path.dirname(doc_path)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建输出文件路径
        file_name = os.path.basename(doc_path)
        docx_name = os.path.splitext(file_name)[0] + '.docx'
        output_path = os.path.join(output_dir, docx_name)
        
        # 对于macOS，使用AppleScript与Word交互
        if sys.platform == 'darwin':  # macOS
            # 创建AppleScript - 更简化版本，避免语法错误
            doc_path_abs = os.path.abspath(doc_path)
            output_path_abs = os.path.abspath(output_path)
            
            script = f'''
            tell application "Microsoft Word"
                open "{doc_path_abs}"
                set doc_file to active document
                save as doc_file file name "{output_path_abs}" file format format docx
                close doc_file
                quit
            end tell
            '''
            
            # 将脚本写入临时文件
            fd, script_path = tempfile.mkstemp(suffix='.scpt')
            os.close(fd)
            
            with open(script_path, 'w') as f:
                f.write(script)
            
            # 执行AppleScript
            cmd = ['osascript', script_path]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            # 删除临时脚本文件
            os.remove(script_path)
            
            if process.returncode != 0:
                print(f"使用Word转换失败: {stderr.decode('utf-8', errors='ignore')}")
                return None
            
            # 检查转换后的文件是否存在
            if os.path.exists(output_path):
                print(f"成功转换: {doc_path} -> {output_path}")
                return output_path
            else:
                print(f"转换后的文件不存在: {output_path}")
                return None
        
        # 对于Windows，使用pywin32
        elif sys.platform == 'win32':  # Windows
            try:
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                
                # 打开文档
                doc = word.Documents.Open(os.path.abspath(doc_path))
                
                # 保存为docx
                doc.SaveAs(os.path.abspath(output_path), 16)  # 16 = wdFormatDocumentDefault (docx)
                doc.Close()
                
                # 如果没有打开的文档，退出Word
                if word.Documents.Count == 0:
                    word.Quit()
                
                if os.path.exists(output_path):
                    print(f"成功转换: {doc_path} -> {output_path}")
                    return output_path
                else:
                    print(f"转换后的文件不存在: {output_path}")
                    return None
            
            except ImportError:
                print("Windows系统需要安装pywin32: pip install pywin32")
                return None
            except Exception as e:
                print(f"使用Word处理doc文件出错: {e}")
                return None
        
        else:
            print(f"不支持的操作系统: {sys.platform}")
            return None
    
    except Exception as e:
        print(f"转换过程中出错: {e}")
        return None

def docx_to_txt(docx_path, output_dir=None, clean=True):
    """
    将docx文件转换为txt，并进行文本清洗
    
    参数:
        docx_path: docx文件路径
        output_dir: 输出目录，默认为None（与原文件相同目录）
        clean: 是否进行文本清洗，默认为True
    
    返回:
        转换后的txt文件路径，如果转换失败则返回None
    """
    try:
        # 如果未指定输出目录，使用原文件所在目录
        if output_dir is None:
            output_dir = os.path.dirname(docx_path)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建输出文件路径
        file_name = os.path.basename(docx_path)
        txt_name = os.path.splitext(file_name)[0] + '.txt'
        output_path = os.path.join(output_dir, txt_name)
        
        # 读取docx文件内容
        doc_text = read_docx(docx_path)
        
        # 如有需要，进行文本清洗
        if clean:
            doc_text = clean_text(doc_text)
        
        # 将文本保存为txt文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc_text)
        
        print(f"成功转换为txt: {docx_path} -> {output_path}")
        return output_path
    
    except Exception as e:
        print(f"转换为txt过程中出错: {e}")
        return None

def doc_to_txt(doc_path, output_dir=None, use_word=True, clean=True, keep_docx=False):
    """
    一步到位将doc文件转换为txt，包括先转为docx，然后读取内容，清洗后保存为txt
    
    参数:
        doc_path: doc文件路径
        output_dir: 输出目录，默认为None（与原文件相同目录）
        use_word: 是否使用Microsoft Word进行转换，默认为True
        clean: 是否进行文本清洗，默认为True
        keep_docx: 是否保留中间生成的docx文件，默认为False
    
    返回:
        转换后的txt文件路径，如果转换失败则返回None
    """
    # 先将doc转换为docx
    if use_word:
        docx_path = convert_doc_to_docx_with_word(doc_path, output_dir)
    else:
        docx_path = convert_doc_to_docx_with_libreoffice(doc_path, output_dir)
    
    if not docx_path:
        return None
    
    # 将docx转换为txt
    txt_path = docx_to_txt(docx_path, output_dir, clean)
    
    # 如果不需要保留docx文件，则删除
    if not keep_docx and os.path.exists(docx_path):
        try:
            os.remove(docx_path)
            print(f"已删除中间docx文件: {docx_path}")
        except Exception as e:
            print(f"删除中间docx文件失败: {e}")
    
    return txt_path

def convert_file_to_txt(file_path, output_dir=None, use_word=True, clean=True, keep_docx=False):
    """
    将单个文件（doc或docx）转换为txt
    
    参数:
        file_path: 文件路径，可以是doc或docx
        output_dir: 输出目录，默认为None（与原文件相同目录）
        use_word: 是否使用Microsoft Word进行转换，默认为True
        clean: 是否进行文本清洗，默认为True
        keep_docx: 是否保留中间生成的docx文件，默认为False
    
    返回:
        转换后的txt文件路径，如果转换失败则返回None
    """
    if file_path.lower().endswith('.doc'):
        # 如果是doc文件，先转为docx再处理
        return doc_to_txt(file_path, output_dir, use_word, clean, keep_docx)
    elif file_path.lower().endswith('.docx'):
        # 如果是docx文件，直接处理
        return docx_to_txt(file_path, output_dir, clean)
    else:
        print(f"不支持的文件格式: {file_path}")
        return None

def batch_convert_to_txt(input_dir, output_dir=None, use_word=True, clean=True, keep_docx=False):
    """
    批量转换目录中的所有doc和docx文件为txt格式
    
    参数:
        input_dir: 输入目录
        output_dir: 输出目录，默认为None（与原文件相同目录）
        use_word: 是否使用Microsoft Word进行转换，默认为True
        clean: 是否进行文本清洗，默认为True
        keep_docx: 是否保留中间生成的docx文件，默认为False
    
    返回:
        成功转换的文件数量
    """
    # 确保输入目录存在
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        return 0
    
    # 查找所有doc和docx文件
    doc_files = glob.glob(os.path.join(input_dir, "**/*.doc"), recursive=True)
    docx_files = glob.glob(os.path.join(input_dir, "**/*.docx"), recursive=True)
    
    all_files = doc_files + docx_files
    
    if not all_files:
        print(f"未找到doc或docx文件: {input_dir}")
        return 0
    
    print(f"找到 {len(doc_files)} 个doc文件和 {len(docx_files)} 个docx文件")
    
    # 转换所有文件
    success_count = 0
    for file_path in tqdm(all_files, desc="正在转换文件"):
        result = convert_file_to_txt(file_path, output_dir, use_word, clean, keep_docx)
        if result:
            success_count += 1
    
    return success_count

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='将doc/docx文件批量转换为txt格式并进行文本清洗')
    parser.add_argument('input_dir', help='包含doc/docx文件的输入目录')
    parser.add_argument('--output-dir', '-o', help='转换后txt文件的输出目录（默认与原文件相同目录）')
    parser.add_argument('--use-libreoffice', '-l', action='store_true', help='使用LibreOffice而不是Microsoft Word进行转换')
    parser.add_argument('--no-clean', '-nc', action='store_true', help='不进行文本清洗')
    parser.add_argument('--keep-docx', '-k', action='store_true', help='保留中间生成的docx文件')
    
    args = parser.parse_args()
    
    print(f"输入目录: {args.input_dir}")
    print(f"输出目录: {args.output_dir or '与输入目录相同'}")
    print(f"使用工具: {'LibreOffice' if args.use_libreoffice else 'Microsoft Word'}")
    print(f"文本清洗: {'否' if args.no_clean else '是'}")
    print(f"保留docx: {'是' if args.keep_docx else '否'}")
    
    # 执行批量转换
    success_count = batch_convert_to_txt(
        args.input_dir, 
        args.output_dir, 
        not args.use_libreoffice, 
        not args.no_clean,
        args.keep_docx
    )
    
    print(f"\n转换完成: 成功转换 {success_count} 个文件")

if __name__ == "__main__":
    main() 