import json
import requests
from pathlib import Path
import os
from docx import Document
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
import logging
import re
import concurrent.futures
import time
from tqdm import tqdm
import random
import traceback
import sys


class LLMExtractor:
    """航天电子元件可靠性分析文档信息提取器"""
    
    def __init__(self, format_json_path, terminology_file=None, server_ip="127.0.0.1", server_port=8000, model_name="gpt-3.5-turbo", api_key=None, api_base=None, debug=False, use_api=None):
        """
        初始化LLM提取器
        
        参数:
            format_json_path: 格式定义JSON文件路径
            terminology_file: 专有名词表文件路径（可选）
            server_ip: API服务器IP地址（本地服务时使用）
            server_port: API服务器端口（本地服务时使用）
            model_name: 使用的模型名称
            api_key: API密钥（使用云服务如OpenAI时必需）
            api_base: API基础URL（使用云服务时可自定义，默认根据是否提供API密钥自动选择）
            debug: 是否启用调试模式
            use_api: 是否强制使用API模式，None表示自动判断（有api_key则使用云API）
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.debug = debug
        self.terminology = []
        self.format_json_path = format_json_path
        self.terminology_file = terminology_file
        
        # 保存格式文件和术语文件的完整路径
        self.format_json_path = os.path.abspath(format_json_path) if format_json_path else None
        self.terminology_file = os.path.abspath(terminology_file) if terminology_file else None
        
        # 根据use_api参数和api_key决定使用何种API调用方式
        if use_api is not None:
            # 显式指定是否使用云API
            self.use_cloud_api = use_api
            # 如果强制使用云API但没有提供API密钥，发出警告
            if self.use_cloud_api and not self.api_key:
                logging.warning("警告：指定使用云API但未提供API密钥，可能导致API调用失败")
        else:
            # 兼容旧逻辑：根据是否提供API密钥决定使用何种API调用方式
            self.use_cloud_api = self.api_key is not None
        
        # 配置日志
        self.logger = logging.getLogger("LLMExtractor")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)
        
        self.logger.info("初始化LLMExtractor...")
        if self.use_cloud_api:
            self.logger.info(f"使用云API模式，模型: {self.model_name}")
        else:
            self.logger.info(f"使用本地API模式，服务器: {self.server_ip}:{self.server_port}")
        
        # 打印完整路径信息
        self.logger.info(f"格式文件完整路径: {self.format_json_path}")
        if self.terminology_file:
            self.logger.info(f"术语文件完整路径: {self.terminology_file}")
        
        # 加载知识库
        self.group_state_map, self.state_values_map = self._prepare_knowledge_index()
        
        # 加载专有名词表（如果提供）
        self.terminology = []
        self.term_to_states = {}
        if self.terminology_file and os.path.exists(self.terminology_file):
            # 直接加载专有名词表
            self.logger.info(f"正在加载专有名词表: {self.terminology_file}")
            with open(self.terminology_file, 'r', encoding='utf-8') as f:
                for line in f:
                    term = line.strip()
                    if term:
                        self.terminology.append(term)
            self.logger.info(f"已加载{len(self.terminology)}个专有名词")
            self.term_to_states = self._build_terminology_mapping()
        
        # 试验项目关键词列表
        self.test_project_keywords = """
    - 外部目检
    - 内部目检
    - 制样镜检
    - 成分分析
    - X射线检查
    - 电性能测试
    - 物理尺寸测量
    - 内部气体成分分析(RGA)
    - 镀层厚度检查
    - 扫描电子显微镜检查（SEM）
    """
        
        self.logger.info("LLMExtractor初始化完成.")
    
    def _prepare_knowledge_index(self):
        """准备知识库索引"""
        self.logger.info(f"正在准备知识库索引: {self.format_json_path}")
        
        try:
            with open(self.format_json_path, 'r', encoding='utf-8') as f:
                format_data = json.load(f)
                
            # 记录文件内容信息以帮助调试
            self.logger.info(f"成功加载格式定义文件，包含{len(format_data)}个条目")
        except Exception as e:
            self.logger.error(f"加载格式定义文件失败: {str(e)}")
            raise
        
        # 构建索引结构
        group_state_map = defaultdict(set)  # 物理状态组 -> 物理状态集合
        state_values_map = defaultdict(lambda: defaultdict(list))  # 物理状态组 -> 物理状态 -> 物理状态值列表
        
        # 填充索引
        for entry in format_data:
            group = entry['物理状态组']
            state = entry['物理状态']
            value = entry['物理状态值']
            
            # 如果有"详细分析"字段但没有"测试评语"字段，将"详细分析"转换为"测试评语"
            if '详细分析' in entry and '测试评语' not in entry:
                entry['测试评语'] = entry.pop('详细分析')
            
            group_state_map[group].add(state)
            state_values_map[group][state].append({
                'value': value,
                'risk': entry['风险评价'],
                'analysis': entry.get('测试评语', ''),  # 使用'测试评语'字段，如果没有则为空字符串
                'test': entry.get('试验项目', '')
            })
        
        self.logger.info(f"知识库索引准备完成，共有{len(group_state_map)}个物理状态组")
        return group_state_map, state_values_map
    
    def _build_terminology_mapping(self):
        """为专有名词建立可能的物理状态映射"""
        self.logger.info(f"正在构建专有名词映射...使用文件: {self.terminology_file}")
        
        try:
            with open(self.format_json_path, 'r', encoding='utf-8') as f:
                knowledge_base = json.load(f)
                self.logger.info(f"成功重新加载格式定义文件用于术语映射")
        except Exception as e:
            self.logger.error(f"加载格式定义文件失败: {str(e)}")
            raise
        
        # 初始化映射
        term_to_states = defaultdict(list)
        
        # 对每个专有名词，在知识库中寻找包含它的物理状态值
        for term in self.terminology:
            for entry in knowledge_base:
                # 检查物理状态值是否包含此专有名词
                if term in entry['物理状态值']:
                    term_to_states[term].append({
                        '物理状态组': entry['物理状态组'],
                        '物理状态': entry['物理状态']
                    })
        
        self.logger.info(f"为{len(term_to_states)}个专有名词建立了物理状态映射")
        return term_to_states
    
    def extract(self, file_path_or_paths, output_dir=None, output_json=True, output_excel=True, batch=True, max_workers=4, batch_by_group=True):
        """
        统一的提取方法，可处理单个文件或多个文件
        
        参数:
            file_path_or_paths: 文档文件路径或文件路径列表
            output_dir: 输出目录，默认为None（输出到各文件所在目录）
            output_json: 是否输出JSON文件
            output_excel: 是否输出Excel文件
            batch: 是否使用批量处理方式
            max_workers: 批量处理时的最大并行工作线程数
            batch_by_group: 批量处理时是否按物理状态组进行批处理
            
        返回:
            单个文件时：提取的结果列表
            多个文件时：文件路径到提取结果的映射字典
        """
        # 判断是单个文件还是多个文件
        is_single_file = isinstance(file_path_or_paths, (str, Path))
        
        # 处理单个文件
        if is_single_file:
            process_type = "批量" if batch else "常规"
            self.logger.info(f"开始{process_type}处理文档: {file_path_or_paths}")
            
            # 读取文档
            try:
                doc = Document(file_path_or_paths)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                
                # 检查文档是否为空
                if not text.strip():
                    self.logger.error(f"文档内容为空: {file_path_or_paths}")
                    return []
                
                # 显示文档信息
                text_length = len(text)
                self.logger.info(f"文档长度: {text_length} 字符")
            
            except Exception as e:
                self.logger.error(f"读取文档失败: {str(e)}")
                return []
            
            # 阶段1: 识别物理状态组和物理状态
            identified_states = self._extract_groups_and_states(text)
            
            # 如果未识别出任何物理状态，尝试备用方法
            if not identified_states:
                self.logger.warning("未识别出任何物理状态组合，尝试备用提取方法...")
                # 注意：这里改为第二次尝试原方法，可以考虑未来实现一个专门的备用方法
                identified_states = self._extract_groups_and_states(text, use_simplified_prompt=True)
            
            # 阶段2: 提取具体值
            extraction_results = self._extract_specific_values(
                text, 
                identified_states, 
                parallel=True, 
                max_workers=max_workers, 
                batch=batch, 
                batch_by_group=batch_by_group
            )
            
            # 标准化结果
            standardized_results = self._standardize_results(extraction_results)
            
            # 确定输出路径
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                base_name = os.path.basename(file_path_or_paths)
                output_base = os.path.join(output_dir, base_name)
                json_output_file = Path(output_base).with_suffix('.json')
                excel_output_file = Path(output_base).with_suffix('.xlsx')
            else:
                json_output_file = Path(file_path_or_paths).with_suffix('.json')
                excel_output_file = Path(file_path_or_paths).with_suffix('.xlsx')
            
            # 保存结果
            if standardized_results:
                if output_json:
                    with open(json_output_file, 'w', encoding='utf-8') as f:
                        json.dump(standardized_results, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"JSON结果已保存到: {json_output_file}")
                
                if output_excel:
                    df = pd.DataFrame(standardized_results)
                    df.to_excel(excel_output_file, index=False)
                    self.logger.info(f"Excel结果已保存到: {excel_output_file}")
            else:
                self.logger.warning("未提取到任何结果，未生成输出文件")
            
            self.logger.info(f"文档{process_type}处理完成: {file_path_or_paths}")
            return standardized_results
            
        # 处理多个文件
        else:
            file_paths = file_path_or_paths
            self.logger.info(f"开始批量处理{len(file_paths)}个文档")
            
            results = {}
            for i, file_path in enumerate(file_paths, 1):
                self.logger.info(f"处理文件 {i}/{len(file_paths)}: {file_path}")
                
                try:
                    # 递归调用处理单个文件
                    result = self.extract(
                        file_path_or_paths=file_path,
                        output_dir=output_dir,
                        output_json=output_json,
                        output_excel=output_excel,
                        batch=batch,
                        max_workers=max_workers,
                        batch_by_group=batch_by_group
                    )
                    
                    results[file_path] = result
                    
                except Exception as e:
                    self.logger.error(f"处理文件 {file_path} 时出错: {str(e)}", exc_info=True)
                    results[file_path] = None
            
            self.logger.info(f"批量处理完成，成功处理{sum(1 for r in results.values() if r)}/{len(file_paths)}个文件")
            return results
            
    
    def _extract_groups_and_states(self, text, use_simplified_prompt=False):
        """识别文档中出现的物理状态组和物理状态"""
        self.logger.info("阶段1: 正在识别文档中的物理状态组和物理状态...")
        
        # 构建提示
        prompt = """请分析以下航天电子元件可靠性分析文档，识别出文档中提到的物理状态组和物理状态。
仅标识出哪些物理状态组和物理状态在文档中被提及，不需要提取具体的物理状态值。

以下是可能的物理状态组和对应的物理状态列表及其典型试验项目：

【封装结构组】
- 封装形式（外部目检）：查找描述"CQFP"、"陶瓷封装"、"引线框架"等词语
- 引线预成型结构（外部目检）：查找描述"已预成型"、"未预成型"等词语
- 引线引出位置（外部目检）：查找描述"顶部"、"中部"、"底部"引出等词语
- 盖板密封工艺（外部目检）：查找描述"焊料环熔封"、"玻璃熔封"、"激光缝焊"等词语
- 管壳密封材料（外部目检、成分分析）：查找描述"金锡"、"玻璃"、"有机胶"等词语
- 管壳材料（外部目检、制样镜检、成分分析）：查找描述"陶瓷"、"金属陶瓷"、"塑料"等词语
- 封装气氛（内部气体成分分析）：查找描述"高纯氮"、"干燥空气"、"真空"等词语
- 封装关键气氛-水汽（内部气体成分分析）：查找描述"水汽"、"ppm"等词语
- 封装关键气氛-氢气（内部气体成分分析）：查找描述"氢气"、"ppm"等词语

【标识组】
- 标识内容完整性（外部目检）：查找描述"标识内容"、"完整"、"缺少"等词语
- 标识工艺（外部目检）：查找描述"油墨印刷"、"激光打标"、"标签粘贴"等词语

【盖板组】
- 盖板基材（制样镜检、成分分析）：查找描述"Ni"、"Fe/Co/Ni"、"玻璃"等词语
- 金属盖板是否接地（X射线检查、电性能测试）：查找描述"接地"、"盖板尺寸"等词语
- 镀层1材料（外部目检、制样镜检、成分分析）：查找描述"镍"、"金"、"银"等词语
- 镀层2/3/4材料（外部目检、制样镜检、成分分析）：查找描述"镀层"、"材料"等词语

【壳体组】
- 壳体材料1/2（外部目检、内部目检、制样镜检、成分分析）：查找描述"氧化铝陶瓷"、"Fe/Co/Ni"等词语
- 镀层1/2/3/4材料（外部目检、内部目检、制样镜检、成分分析）：查找描述"镀层"、"镍"、"金"等词语
- 陶瓷壳体内部金属化布线材料（制样镜检、成分分析）：查找描述"W"、"Mo"等词语
- 通孔材料（制样镜检、成分分析）：查找描述"W"、"Mo"等词语

【安全间距组】
- 芯片与腔体侧壁间距（外部目检、内部目检、物理尺寸）：查找描述"芯片"、"侧壁"、"间距"等词语
- 键合丝间间距（外部目检、内部目检、物理尺寸）：查找描述"键合丝"、"间距"、"搭接"等词语
- 键合丝与盖板间距（外部目检、内部目检、物理尺寸）：查找描述"键合丝"、"盖板"、"间距"等词语
- 内部元器件与盖板间距（外部目检、内部目检、物理尺寸）：查找描述"内部元器件"、"盖板"、"间距"等词语
- 键合丝与壳体间距（外部目检、内部目检、物理尺寸）：查找描述"键合丝"、"壳体"、"间距"等词语
- 引出端最小绝缘间距（外部目检、内部目检、物理尺寸）：查找描述"引出端"、"绝缘"、"间距"等词语
- 键合点间间距（外部目检、内部目检、物理尺寸）：查找描述"键合点"、"间距"等词语

【热沉组】
- 热沉结构（制样镜检）：查找描述"一体式热沉"、"分体式热沉"等词语
- 热沉材料（外部目检、制样镜检、成分分析）：查找描述"钢"、"铁镍"、"钼铜"等词语
- 镀层1/2/3/4材料（外部目检、内部目检、制样镜检、成分分析）：查找描述"镀层"、"材料"等词语

【引出端组】
- 引出端与壳体连接方式（外部目检、内部目检、制样镜检、成分分析）：查找描述"银铜焊接"、"陶瓷绝缘子"等词语
- 引出端材料（外部目检、制样镜检、成分分析）：查找描述"纯锡"、"铅锡"、"铜芯可伐"等词语
- 引出端形状（外部目检）：查找描述"焊球"、"焊柱"、"垂直引出"等词语
- 镀层1/2/3/4材料（外部目检、内部目检、制样镜检、成分分析）：查找描述"镀层"、"材料"等词语

【芯片平面结构组】
- 芯片安装形式（内部目检、制样镜检）：查找描述"正装"、"倒装"、"叠层安装"等词语
- 表面金属化材料（内部目检、制样镜检、成分分析、SEM）：查找描述"金"、"铜"、"银"等词语
- 表面钝化层材料（内部目检、制样镜检、成分分析、SEM）：查找描述"氮化硅"、"氧化硅"、"聚酰亚胺"等词语
- 背金材料（内部目检、制样镜检、成分分析、SEM）：查找描述"钒镍金"、"钛镍银"、"无背金"等词语

【芯片纵向结构组】
- 金属化层数（内部目检、制样镜检、成分分析、SEM）：查找描述"金属化层"、"层数"等词语
- 多晶层数（内部目检、制样镜检、成分分析、SEM）：查找描述"多晶"、"层数"等词语
- 接触孔、通孔工艺（内部目检、制样镜检、成分分析、SEM）：查找描述"W"、"Mo"、"Cu"、"TSV"等词语
- 层间介质材料（内部目检、制样镜检、成分分析、SEM）：查找描述"氧化硅"、"氮化硅"、"氧化铪"等词语
- 划片方式（内部目检、制样镜检、SEM）：查找描述"全深度划片"、"非全深度划片"、"激光划片"等词语

【芯片安装组】
- 安装方式（内部目检）：查找描述"焊接"、"粘接"等词语
- 安装材料（内部目检、制样镜检、成分分析）：查找描述"导电胶"、"有机胶"、"AuSn"等词语

【键合结构组】
- 丝径（内部目检）：查找描述"丝径"、"微米"等词语
- 键合丝材料（内部目检、制样镜检、成分分析）：查找描述"Au"、"硅铝丝"、"铝丝"等词语
- 芯片端键合区域材料（内部目检、制样镜检、成分分析）：查找描述"Cu"、"Al"、"Ag"等词语
- 非芯片端键合区域材料（内部目检、制样镜检、成分分析）：查找描述"Cu"、"Al"、"Ag"等词语
- 键合工艺（内部目检）：查找描述"超声楔形键合"、"球形键合"等词语
- 键合界面（内部目检、制样镜检）：查找描述"同质键合"、"异质键合"、"复合键合"等词语

在文档分析中，请注意以下结构关联：
1. "标识部分"章节通常包含标识组相关物理状态
2. "器件封装结构"章节通常包含封装结构组相关物理状态
3. "芯片"章节通常包含芯片平面结构、芯片纵向结构相关物理状态
4. "键合系统"章节通常包含键合结构相关物理状态

领域表达解析指南：
- "器件采用CQFP48陶瓷封装" → 封装结构-封装形式
- "开帽后进行内部目检" → 试验项目为"内部目检"
- "通过X射线对器件封装结构进行检查" → 试验项目为"X射线检查"
- "盖板采用Fe/Ni合金" → 盖板-盖板基材
- "外管脚材料为可伐材料镀Ni再镀Au" → 引出端-引出端材料、引出端-镀层材料
- "内引线采用铝丝键合" → 键合结构-键合丝材料
- "芯片直接通过银浆粘接" → 芯片安装-安装材料

请仔细分析文档内容，寻找与上述物理状态组和物理状态相关的描述。
即使文档中没有明确使用这些术语，也请基于文档内容推断可能涉及的物理状态。"""
        
        # 如果有专有名词，也添加到提示中
        if self.terminology:
            prompt += "\n\n以下是领域专有名词表，请特别关注文档中出现的这些术语："
            
            # 每行添加5个专有名词，避免prompt过长
            terms_per_line = 5
            for i in range(0, len(self.terminology), terms_per_line):
                terms_line = "、".join(self.terminology[i:i+terms_per_line])
                prompt += f"\n{terms_line}"
        
        prompt += """

以JSON格式返回文档中提到的物理状态组和物理状态，格式如下：
{
    "identified_states": [
        {"物理状态组": "封装结构", "物理状态": "封装形式"},
        {"物理状态组": "标识", "物理状态": "标识工艺"},
        ...
    ]
}

文本内容：
"""
        
        # 限制文本长度，避免超出模型的处理能力
        max_text_length = 12000  # 根据模型能力调整，避免超过模型的token限制
        if len(text) > max_text_length:
            # 取文本的前一部分和后一部分，中间部分用省略号替代
            text_front = text[:max_text_length//2]
            text_back = text[-max_text_length//2:]
            truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
            prompt += truncated_text
        else:
            prompt += text
        
        # 调用LLM API
        result = self._call_llm_api(prompt)
        
        if self.debug:
            self.logger.debug(f"API响应: {result[:500]}...")
        
        # 解析结果
        try:
            # 从结果中提取JSON部分
            json_str = self._extract_json_from_response(result)
            if not json_str:
                self.logger.error("无法从响应中提取JSON")
                return []
                    
            data = json.loads(json_str)
            
            # 处理大小写问题
            if "identified_States" in data and "identified_states" not in data:
                data["identified_states"] = data.pop("identified_States")
                self.logger.debug("已将'identified_States'(大写S)转换为'identified_states'(小写s)")
            
            identified_states = data.get("identified_states", [])
            
            self.logger.info(f"识别出{len(identified_states)}个物理状态组合")
            for item in identified_states:
                self.logger.debug(f"  - {item['物理状态组']} -> {item['物理状态']}")
            
            return identified_states
        except Exception as e:
            self.logger.error(f"解析阶段1结果失败: {e}")
            self.logger.debug(f"原始结果: {result}")
            return []
    
    
    def _extract_specific_values(self, text, identified_states, parallel=True, max_workers=4, batch=False, batch_by_group=True):
        """提取具体的物理状态值，支持并行处理和批处理
        
        参数:
            text: 文档文本内容
            identified_states: 识别出的物理状态组合列表
            parallel: 是否使用并行处理
            max_workers: 并行处理时的最大工作线程数
            batch: 是否使用批处理模式
            batch_by_group: 批处理模式下是否按物理状态组分组处理
        
        返回:
            提取结果的列表
        """
        # 根据参数选择合适的处理模式
        if batch:
            self.logger.info(f"阶段2: 正在批量提取具体的物理状态值（最大并行数：{max_workers}，按组批处理：{batch_by_group}）...")
        elif parallel:
            self.logger.info(f"阶段2: 正在并行提取具体的物理状态值（最大并行数：{max_workers}）...")
        else:
            self.logger.info("阶段2: 正在提取具体的物理状态值...")
        
        if not identified_states:
            self.logger.warning("没有识别出物理状态组合，无法提取具体值")
            return []
        
        # 测试评语指南（统一格式）
        test_comment_guide = """
测试评语应具有以下特点：
1. 简明扼要：通常不超过1-2句话
2. 重点突出：强调测试的主要发现和结论
3. 评价明确：使用"良好"、"合格"、"正常"、"异常"等评价性词语
4. 结论性强：明确指出是否存在可靠性隐患
5. 适合测试报告使用：用语专业规范

示例：
- "油墨印刷标识牢固度良好，满足宇航应用要求"
- "CQFP48陶瓷封装结构正常，无可靠性隐患"
- "芯片钝化层完整，覆盖良好，无异常现象"
- "键合强度测试数据合格，具有良好一致性和裕度"
"""
        
        results = []
        
        # 批处理模式
        if batch:
            # 如果按组批处理，将相同物理状态组的状态分组
            if batch_by_group:
                # 按物理状态组分组
                groups = {}
                for item in identified_states:
                    group = item['物理状态组']
                    if group not in groups:
                        groups[group] = []
                    groups[group].append(item)
                
                # 打印分组信息
                group_counts = {g: len(s) for g, s in groups.items()}
                self.logger.debug(f"物理状态组分组情况: {group_counts}")
                
                # 计算批次数量
                batch_count = len(groups)
                self.logger.info(f"将{len(identified_states)}个物理状态组合分为{batch_count}个批次处理")
                
                # 创建任务列表
                tasks = []
                for group, states in groups.items():
                    tasks.append((group, states))
                
                # 处理各个批次
                with tqdm(total=batch_count, desc="处理物理状态组") as pbar:
                    if parallel and max_workers > 1:
                        # 并行处理各个批次
                        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                            future_to_group = {executor.submit(self._process_single_batch, text, group, states): group for group, states in tasks}
                            
                            for future in concurrent.futures.as_completed(future_to_group):
                                group = future_to_group[future]
                                try:
                                    batch_results = future.result()
                                    if batch_results:
                                        self.logger.info(f"成功从物理状态组 '{group}' 提取{len(batch_results)}个结果")
                                        results.extend(batch_results)
                                    else:
                                        self.logger.warning(f"从物理状态组 '{group}' 提取结果失败")
                                except Exception as e:
                                    self.logger.error(f"处理物理状态组 '{group}' 时出错: {e}")
                                finally:
                                    pbar.update(1)
                    else:
                        # 串行处理各个批次
                        for group, states in tasks:
                            try:
                                batch_results = self._process_single_batch(text, group, states)
                                if batch_results:
                                    self.logger.info(f"成功从物理状态组 '{group}' 提取{len(batch_results)}个结果")
                                    results.extend(batch_results)
                                else:
                                    self.logger.warning(f"从物理状态组 '{group}' 提取结果失败")
                            except Exception as e:
                                self.logger.error(f"处理物理状态组 '{group}' 时出错: {e}")
                            finally:
                                pbar.update(1)
            else:
                # 不按组分组，而是每3个状态一组进行批处理
                total_items = len(identified_states)
                batch_size = 3
                num_batches = (total_items + batch_size - 1) // batch_size
                
                self.logger.info(f"将{total_items}个物理状态组合分为{num_batches}个批次处理（每批{batch_size}个）")
                
                with tqdm(total=num_batches, desc="处理批次") as pbar:
                    for i in range(0, total_items, batch_size):
                        batch = identified_states[i:i+batch_size]
                        
                        for item in batch:
                            group = item['物理状态组']
                            states = [item]
                            
                            try:
                                batch_results = self._process_single_batch(text, group, states)
                                if batch_results:
                                    results.extend(batch_results)
                            except Exception as e:
                                self.logger.error(f"处理物理状态组 '{group}' 时出错: {e}")
                        
                        pbar.update(1)
        # 常规单个处理模式（串行或并行）
        else:
            total = len(identified_states)
            
            def process_item(item):
                """处理单个物理状态组合"""
                group = item['物理状态组']
                state = item['物理状态']
                
                # 查找与此物理状态相关的专有名词
                relevant_terms = []
                if self.terminology:
                    for term in self.terminology:
                        if term.lower() in text.lower() and (
                            term.lower() in group.lower() or 
                            term.lower() in state.lower() or
                            len(term) > 2  # 避免短的、常见的词
                        ):
                            relevant_terms.append(term)
                
                # 构建提示
                prompt = f"""请从以下文本中提取关于"{group}"的"{state}"的具体物理状态值、风险评价和测试评语信息。

【试验项目指导】
试验项目通常包括以下关键词"{self.test_project_keywords}"，请重点关注与此相关的描述。

【风险评价判断标准】
分析风险评价时，请注意以下规则：
- "可用"：描述中包含"常规结构"、"无可靠性隐患"、"工艺良好"、"满足宇航应用要求"等正面评价
- "限用"：描述中包含"存在风险"、"限制条件使用"、"建议评估后使用"、"限进行处理措施后使用"等条件性评价
- "禁用"：描述中包含"不适合宇航应用"、"有可靠性隐患"、"不满足标准要求"、"超标"等否定性评价

【物理状态值标准化指南】
为确保提取的物理状态值符合标准格式，请参考以下表达映射：
- "{group}"-"{state}"的标准物理状态值范围包括常见行业表达
- 当文档描述类似时，应提取为对应的标准物理状态值

【专有名词解释】
物理状态相关专有名词解析：
- CQFP：陶瓷方形扁平封装
- CMP：化学机械抛光工艺
- 银浆：银颗粒与有机材料组成的导电粘合剂，用于芯片粘接
- 弓丝弧度：键合丝的曲线形态
- 键合拉力：测试键合丝与键合点间的连接牢固度的测试
- 玻璃钝化层：保护芯片表面的绝缘保护层
- 绝缘筋：用于保护和隔离管脚的结构

【测试评语指南】
测试评语应具有以下特点：
1. 简明扼要：通常不超过1-2句话
2. 重点突出：强调测试的主要发现和结论
3. 评价明确：使用"良好"、"合格"、"正常"、"异常"等评价性词语
4. 结论性强：明确指出是否存在可靠性隐患
5. 适合测试报告使用：用语专业规范

返回格式：
{{
    "物理状态组": "{group}",
    "物理状态": "{state}",
    "试验项目": "从文本中提取的试验项目",
    "物理状态值": "从文本中提取的物理状态值",
    "风险评价": "可用/限用/禁用（从文本判断）",
    "测试评语": "从文本中提取的简洁测试评价"
}}

如果文本中确实没有相关信息，请在"物理状态值"字段中填写"文中未提及"，在"测试评语"中填写"文档中未包含此信息"。"""
                
                # 添加相关专有名词提示
                if relevant_terms:
                    prompt += f"\n\n以下是可能与'{group}'的'{state}'相关的专有名词，请特别关注这些术语在文本中的出现：\n"
                    prompt += "、".join(relevant_terms) + "\n"
                
                prompt += f"""
返回格式：
{{
    "物理状态组": "{group}",
    "物理状态": "{state}",
    "试验项目": "从文本中提取的试验项目",
    "物理状态值": "从文本中提取的物理状态值",
    "风险评价": "可用/限用/禁用（从文本判断）",
    "测试评语": "从文本中提取的简洁测试评价"
}}

如果文本中确实没有相关信息，请在"物理状态值"字段中填写"文中未提及"，在"测试评语"中填写"文档中未包含此信息"。

文本内容：
"""
                
                # 限制文本长度，避免超出模型的处理能力
                max_text_length = 12000  # 根据模型能力调整，避免超过模型的token限制
                if len(text) > max_text_length:
                    # 取文本的前一部分和后一部分，中间部分用省略号替代
                    text_front = text[:max_text_length//2]
                    text_back = text[-max_text_length//2:]
                    truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
                    prompt += truncated_text
                else:
                    prompt += text
                
                # 调用LLM API
                result = self._call_llm_api(prompt)
                
                if self.debug and not parallel:
                    self.logger.debug(f"阶段2 API响应: {result[:500]}...")
                
                # 解析结果
                try:
                    # 从结果中提取JSON部分
                    json_str = self._extract_json_from_response(result)
                    if not json_str:
                        self.logger.warning(f"  无法从响应中提取JSON，跳过 {group} - {state}")
                        if parallel:
                            return None
                        else:
                            return
                        
                    extracted_item = json.loads(json_str)
                    
                    # 验证必要字段
                    required_fields = ["物理状态组", "物理状态", "物理状态值"]
                    if all(field in extracted_item for field in required_fields):
                        # 如果物理状态值为"文中未提及"，跳过该项
                        if extracted_item["物理状态值"] == "文中未提及":
                            self.logger.debug(f"  物理状态值为'文中未提及'，跳过")
                            if parallel:
                                return None
                            else:
                                return
                        
                        self.logger.debug(f"  提取值: {extracted_item['物理状态值']}")
                        if parallel:
                            return extracted_item
                        else:
                            results.append(extracted_item)
                    else:
                        self.logger.warning(f"  警告: 提取结果缺少必要字段")
                        self.logger.debug(f"  结果: {extracted_item}")
                        if parallel:
                            return None
                except Exception as e:
                    self.logger.error(f"  解析失败: {e}")
                    if parallel:
                        return None
            
            # 并行处理
            if parallel:
                # 使用线程池执行并行处理
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 创建一个任务映射
                    future_to_item = {executor.submit(process_item, item): item for item in identified_states}
                    
                    # 创建进度条
                    with tqdm(total=total, desc="提取进度") as pbar:
                        # 处理完成的任务
                        for future in concurrent.futures.as_completed(future_to_item):
                            item = future_to_item[future]
                            try:
                                result = future.result()
                                if result:
                                    results.append(result)
                            except Exception as e:
                                self.logger.error(f"处理 {item['物理状态组']} - {item['物理状态']} 时出错: {e}")
                            finally:
                                pbar.update(1)
            # 串行处理
            else:
                # 使用简单的循环处理每个项
                for i, item in enumerate(identified_states, 1):
                    group = item['物理状态组']
                    state = item['物理状态']
                    
                    self.logger.info(f"处理 {i}/{total}: {group} - {state}")
                    process_item(item)
        
        self.logger.info(f"成功提取{len(results)}个物理状态值")
        return results
    
    def _standardize_results(self, extracted_results):
        """标准化提取结果，与知识库匹配"""
        self.logger.info("正在标准化结果...")
        
        if not extracted_results:
            self.logger.warning("没有提取结果，跳过标准化")
            return []
        
        standardized_results = []
        
        for item in extracted_results:
            # 检查必要字段是否存在
            if '物理状态组' not in item or '物理状态值' not in item:
                self.logger.warning(f"跳过不完整的结果: {item}")
                continue
                
            group = item['物理状态组']
            
            # 确保物理状态字段存在
            if '物理状态' not in item:
                self.logger.warning(f"结果缺少'物理状态'字段，尝试从其他字段推断")
                # 尝试从列表中找到匹配的物理状态
                matched_states = []
                if group in self.group_state_map:
                    for possible_state in self.group_state_map[group]:
                        # 检查是否在item的值中提到了这个物理状态
                        state_mentioned = False
                        for value in item.values():
                            if isinstance(value, str) and possible_state in value:
                                state_mentioned = True
                                break
                        if state_mentioned:
                            matched_states.append(possible_state)
                
                if matched_states:
                    # 使用最可能的物理状态
                    item['物理状态'] = matched_states[0]
                    self.logger.info(f"为结果推断物理状态: {matched_states[0]}")
                else:
                    # 如果无法推断，使用默认值
                    item['物理状态'] = "未知状态"
                    self.logger.warning(f"无法推断物理状态，使用默认值: 未知状态")
            
            state = item['物理状态']
            extracted_value = item['物理状态值']
            
            # 如果有"详细分析"字段但没有"测试评语"字段，将"详细分析"转换为"测试评语"
            if '详细分析' in item and '测试评语' not in item:
                item['测试评语'] = item.pop('详细分析')
            
            # 确保所有必要字段都存在
            if '测试评语' not in item:
                item['测试评语'] = "无评语"
            
            if '风险评价' not in item:
                item['风险评价'] = "可用"  # 默认为可用
                
            if '试验项目' not in item:
                item['试验项目'] = ""
            
            self.logger.debug(f"处理: {group} - {state} - {extracted_value}")
            
            # 检查提取值中是否包含专有名词
            contained_terms = []
            if self.terminology:
                for term in self.terminology:
                    if term in extracted_value:
                        contained_terms.append(term)
            
            if contained_terms:
                self.logger.debug(f"  包含专有名词: {', '.join(contained_terms)}")
            
            # 尝试在知识库中找到匹配项
            if group in self.state_values_map and state in self.state_values_map[group]:
                # 寻找最匹配的物理状态值
                best_match = None
                best_match_score = 0
                
                for kb_item in self.state_values_map[group][state]:
                    # 基础相似度评分
                    base_score = SequenceMatcher(None, extracted_value, kb_item['value']).ratio()
                    
                    # 专有名词加权
                    term_bonus = 0
                    for term in contained_terms:
                        if term in kb_item['value']:
                            term_bonus += 0.1
                    
                    final_score = base_score + term_bonus
                    
                    if final_score > best_match_score:
                        best_match_score = final_score
                        best_match = kb_item
                
                # 如果找到较好匹配，使用知识库中的standard字段作为测试评语
                if best_match_score > 0.6:  # 降低匹配阈值以增加匹配成功率
                    self.logger.debug(f"  找到匹配项: {best_match['value']} (相似度: {best_match_score:.2f})")
                    
                    # 使用知识库中的analysis字段作为测试评语
                    analysis_content = best_match.get('analysis', '')
                    
                    standardized_item = {
                        "物理状态组": group,
                        "物理状态": state,
                        "试验项目": best_match['test'],
                        "物理状态值": best_match['value'],
                        "风险评价": best_match['risk'],
                        "测试评语": analysis_content
                    }
                else:
                    self.logger.debug(f"  无良好匹配，保留原始提取值")
                    # 确保使用"测试评语"字段
                    if "详细分析" in item and "测试评语" not in item:
                        item["测试评语"] = item.pop("详细分析")
                    standardized_item = item
            else:
                self.logger.debug(f"  知识库中无此组合，保留原始提取值")
                # 确保使用"测试评语"字段
                if "详细分析" in item and "测试评语" not in item:
                    item["测试评语"] = item.pop("详细分析")
                standardized_item = item
            
            standardized_results.append(standardized_item)
        
        self.logger.info(f"标准化完成，共{len(standardized_results)}个结果")
        return standardized_results
    
    def _call_llm_api(self, prompt, max_retries=3, retry_delay=2):
        """调用LLM API（包含重试机制）
        
        参数:
            prompt: 发送给API的提示词
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            
        返回:
            API响应内容，如果失败则返回空字符串
        """
        # 生成请求ID用于保存中间结果
        request_id = f"api_call_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # 保存请求信息
        if hasattr(self, 'intermediate_dir'):
            self._save_intermediate_result(request_id, {
                "prompt": prompt,
                "max_retries": max_retries,
                "retry_delay": retry_delay
            })
        
        # 根据是否使用云API决定调用方式
        if self.use_cloud_api:
            # 使用云API（如OpenAI的API）
            if self.api_base:
                url = f"{self.api_base}/chat/completions"
            else:
                # 默认使用OpenAI API
                url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            data = {
                'model': self.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.01,
            }
        else:
            # 使用本地API服务器
            url = f'http://{self.server_ip}:{self.server_port}/api/chat'
            headers = {'Content-Type': 'application/json'}
            data = {
                'model': self.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'options': {'temperature': 0.01},
                'stream': True
            }
        
        if self.debug:
            self.logger.debug(f"API请求: {url}")
            self.logger.debug(f"请求参数: {json.dumps(data, ensure_ascii=False)[:500]}...")
        
        # 执行重试逻辑
        for attempt in range(max_retries):
            try:
                # 添加随机短延迟，避免大量请求同时发送
                if attempt > 0:  # 仅在重试时添加延迟
                    jitter = random.uniform(0, 1)
                    current_delay = retry_delay * (1.5 ** (attempt - 1)) + jitter
                    self.logger.warning(f"第{attempt+1}次重试，延迟{current_delay:.2f}秒...")
                    time.sleep(current_delay)
                
                # 记录开始时间
                start_time = time.time()
                
                # 根据API类型执行不同的调用逻辑
                if self.use_cloud_api:
                    # 调用云API
                    response = requests.post(url, headers=headers, json=data)
                    response.raise_for_status()
                    response_json = response.json()
                    
                    # 从标准OpenAI格式响应中提取内容
                    if 'choices' in response_json and len(response_json['choices']) > 0:
                        content = response_json['choices'][0]['message']['content']
                    else:
                        self.logger.warning(f"无法从API响应中解析内容: {response_json}")
                        content = ""
                else:
                    # 使用本地服务器（流式响应）
                    content = ""
                    with requests.post(url, headers=headers, json=data, stream=True) as response:
                        response.raise_for_status()
                        
                        for line in response.iter_lines(decode_unicode=True):
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    chunk_content = chunk['message']['content']
                                    content += chunk_content
                                except json.JSONDecodeError:
                                    continue
                
                # 计算响应时间
                response_time = time.time() - start_time
                
                # 保存响应结果
                if hasattr(self, 'intermediate_dir'):
                    self._save_intermediate_result(f"{request_id}_response_{attempt+1}", {
                        "content": content[:2000],  # 仅保存前2000个字符，避免文件过大
                        "content_length": len(content),
                        "attempt": attempt + 1,
                        "response_time": response_time
                    })
                
                if not content:
                    self.logger.warning(f"API返回空响应，尝试重试 ({attempt+1}/{max_retries})")
                    continue
                
                self.logger.debug(f"API调用成功，耗时: {response_time:.2f}秒")
                return content
            
            except Exception as e:
                # 捕获API调用过程中的错误
                if hasattr(self, 'intermediate_dir'):
                    self._save_intermediate_result(f"{request_id}_error_{attempt+1}", {
                        "exception": str(e),
                        "traceback": traceback.format_exc() if 'traceback' in sys.modules else str(e),
                        "attempt": attempt + 1
                    })
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"API调用失败，将重试 ({attempt+1}/{max_retries}): {str(e)}")
                else:
                    self.logger.error(f"API调用在{max_retries}次尝试后失败: {str(e)}")
        
        # 所有重试都失败
        return ""
    
    def _extract_json_from_response(self, response, is_array=False):
        """从LLM响应中提取JSON部分
        
        参数:
            response: LLM的响应文本
            is_array: 是否需要提取JSON数组（默认为False，提取单个JSON对象）
            
        返回:
            提取出的JSON字符串，如果无法提取则返回空字符串
        """
        if not response:
            return ""
            
        # 记录原始响应以便调试
        if len(response) > 1000:
            self.logger.debug(f"提取JSON前的响应 (截取): {response[:500]}...{response[-500:]}")
        else:
            self.logger.debug(f"提取JSON前的响应: {response}")
        
        # 首先尝试提取指定类型的JSON
        if is_array:
            # 提取JSON数组
            
            # 方法1: 寻找数组格式的JSON
            array_regex = r'(\[\s*\{[\s\S]*\}\s*\])'
            array_matches = re.findall(array_regex, response)
            
            if array_matches:
                for potential_array in array_matches:
                    try:
                        # 验证是否为有效JSON数组
                        json.loads(potential_array)
                        return potential_array
                    except:
                        continue
            
            # 方法2: 寻找Markdown代码块中的JSON数组
            markdown_regex = r'```(?:json)?\s*([\s\S]*?)```'
            markdown_matches = re.findall(markdown_regex, response)
            
            if markdown_matches:
                for potential_json in markdown_matches:
                    # 在代码块中查找JSON数组
                    array_in_block = re.findall(r'(\[\s*\{[\s\S]*\}\s*\])', potential_json)
                    if array_in_block:
                        for array_json in array_in_block:
                            try:
                                # 验证是否为有效JSON数组
                                json.loads(array_json)
                                return array_json
                            except:
                                continue
            
            # 方法3: 查找最外层的方括号
            if '[' in response and ']' in response:
                start_idx = response.find('[')
                end_idx = response.rfind(']')
                
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    array_str = response[start_idx:end_idx+1]
                    try:
                        # 验证是否为有效JSON数组
                        parsed = json.loads(array_str)
                        if isinstance(parsed, list):
                            return array_str
                    except:
                        pass
            
            # 如果优先提取数组但未成功，尝试提取单个对象并包装成数组
            obj_json = self._extract_json_from_response(response, is_array=False)
            if obj_json:
                try:
                    # 验证是否为有效JSON对象
                    obj = json.loads(obj_json)
                    if isinstance(obj, dict):
                        # 将单个对象包装为数组
                        array_str = f"[{obj_json}]"
                        return array_str
                except:
                    pass
        else:
            # 提取单个JSON对象
            
            # 方法1: 寻找JSON对象
            json_regex = r'({[\s\S]*})'
            json_matches = re.findall(json_regex, response)
            
            if json_matches:
                for potential_json in json_matches:
                    try:
                        # 验证是否为有效JSON
                        json.loads(potential_json)
                        return potential_json
                    except:
                        continue
            
            # 方法2: 寻找Markdown代码块中的JSON
            markdown_regex = r'```(?:json)?\s*([\s\S]*?)```'
            markdown_matches = re.findall(markdown_regex, response)
            
            if markdown_matches:
                for potential_json in markdown_matches:
                    try:
                        # 尝试找到并提取JSON对象
                        start_idx = potential_json.find('{')
                        end_idx = potential_json.rfind('}')
                        
                        if start_idx != -1 and end_idx != -1:
                            json_str = potential_json[start_idx:end_idx+1]
                            # 验证是否为有效JSON
                            json.loads(json_str)
                            return json_str
                    except:
                        continue
            
            # 方法3: 最后的尝试，寻找最外层的花括号
            if '{' in response and '}' in response:
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    json_str = response[start_idx:end_idx+1]
                    try:
                        # 验证是否为有效JSON
                        json.loads(json_str)
                        return json_str
                    except:
                        pass
                        
            # 如果优先提取对象但未成功，尝试从数组中提取第一个对象
            if not is_array:  # 避免无限递归
                array_json = self._extract_json_from_response(response, is_array=True)
                if array_json:
                    try:
                        # 尝试解析数组并返回第一个对象
                        array = json.loads(array_json)
                        if isinstance(array, list) and array and isinstance(array[0], dict):
                            return json.dumps(array[0], ensure_ascii=False)
                    except:
                        pass
        
        # 都未成功
        return ""
    
    def _process_single_batch(self, text, group, states):
        """处理单个批次的状态组合，简化提示和错误处理"""
        # 每个状态准备一个简单的描述
        states_str = "\n".join([f"- {state['物理状态']}" for state in states])
        

        # 构建简化的提示，更明确地要求LLM返回JSON数组
        prompt = f"""请分析以下文本，提取关于"{group}"物理状态组的以下物理状态信息：

{states_str}

【重要限制：仅处理当前组】
请严格只提取"{group}"物理状态组的信息，不要返回任何其他物理状态组的信息。
每个结果必须是"{group}"组下的一个物理状态，且物理状态必须是上述列出的其中之一。
如果识别到其他组的信息，请完全忽略，不要在结果中包含。

【物理状态名称严格限制】
请注意：返回的"物理状态"字段值必须严格从以下列表中选择，不要使用其他名称（如试验项目名称等）：
{states_str}

【试验项目指导】
试验项目通常包括以下关键词"{self.test_project_keywords}"，请重点关注与此相关的描述。

【风险评价判断标准】
风险评价判断时，请遵循以下规则：
- "可用"通常对应描述："常规结构"、"无可靠性隐患"、"满足宇航应用要求"
- "限用"通常对应描述："存在风险"、"建议评估后使用"、"限制条件使用"
- "禁用"通常对应描述："不适合宇航应用"、"严重隐患"、"不满足标准要求"

【物理状态值提取指南】
请基于文档内容提取物理状态值，注意以下标准化规则：
- 当描述类似于常见行业表达时，应提取为对应的标准物理状态值
- 尽量提取具体数值或明确表述，避免模糊表达

【典型值-风险关联参考】
以下是典型的物理状态值与风险评价关联：
- 符合行业标准、规范要求的通常为"可用"
- 存在一定局限性或需要特定条件的通常为"限用"
- 不符合宇航要求或有明显隐患的通常为"禁用"

【文档结构解析指南】
在航天电子元件可靠性分析文档中：
- "详细分析"章节通常包含关键物理状态描述
- 表述如"常规结构，无可靠性隐患"通常表明该物理状态"可用"
- 提到某试验项目时，应关注与该试验相关的物理状态

【测试评语提取指南】
测试评语应具有以下特点：
1. 简明扼要：通常不超过1-2句话
2. 重点突出：强调测试的主要发现和结论
3. 评价明确：使用"良好"、"合格"、"正常"、"异常"等评价性词语
4. 结论性强：明确指出是否存在可靠性隐患
5. 适合测试报告使用：用语专业规范

请以JSON数组格式返回提取结果：
[
    {{
        "物理状态组": "{group}",
        "物理状态": "第一个物理状态名称",
        "试验项目": "提取的试验项目",
        "物理状态值": "提取的物理状态值",
        "风险评价": "可用/限用/禁用",
        "测试评语": "提取的测试评语"
    }},
    {{
        "物理状态组": "{group}",
        "物理状态": "第二个物理状态名称",
        "试验项目": "提取的试验项目",
        "物理状态值": "提取的物理状态值",
        "风险评价": "可用/限用/禁用",
        "测试评语": "提取的测试评语"
    }}
    ...
]

如果某物理状态在文档中未提及，请将其"物理状态值"设为"文中未提及"。

文本内容：
"""
        
        # 限制文本长度，避免超出模型的处理能力
        max_text_length = 12000  # 根据模型能力调整，避免超过模型的token限制
        if len(text) > max_text_length:
            # 取文本的前一部分和后一部分，中间部分用省略号替代
            text_front = text[:max_text_length//2]
            text_back = text[-max_text_length//2:]
            truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
            prompt += truncated_text
        else:
            prompt += text
        
        # 调用LLM API（带重试机制）
        result = self._call_llm_api(prompt)
        
        if not result:
            self.logger.warning(f"API返回空响应，跳过物理状态组 '{group}'")
            return []
            
        batch_results = []
        
        # 尝试直接解析为JSON数组
        json_str = self._extract_json_from_response(result, is_array=True)
        if not json_str:
            self.logger.warning(f"无法从批处理响应中提取JSON数组，尝试查找单个JSON对象")
            # 尝试查找单个JSON对象
            json_str = self._extract_json_from_response(result)
            if json_str:
                try:
                    single_item = json.loads(json_str)
                    if isinstance(single_item, dict):
                        # 确保物理状态组一致
                        if "物理状态组" in single_item:
                            if single_item["物理状态组"] != group:
                                # 不匹配时，记录并返回空结果
                                self.logger.warning(f"跳过不匹配的物理状态组：{single_item['物理状态组']}（期望：{group}）")
                                return []  # 返回空结果代替continue
                        else:
                            single_item["物理状态组"] = group
                                
                        # 检查是否包含关键字段
                        if "物理状态组" in single_item and "物理状态值" in single_item:
                            # 确保所有必需字段存在
                            if "物理状态" not in single_item:
                                # 尝试从状态列表中推断
                                for state_info in states:
                                    if state_info["物理状态"] in result:
                                        single_item["物理状态"] = state_info["物理状态"]
                                        break
                                if "物理状态" not in single_item:
                                    self.logger.warning(f"无法确定物理状态，使用默认值")
                                    single_item["物理状态"] = "未知状态"
                            
                            if single_item.get("物理状态值", "") != "文中未提及":
                                batch_results.append(single_item)
                                self.logger.debug(f"单独提取成功: {single_item.get('物理状态', '未知')} - {single_item['物理状态值']}")
                            # 特殊处理标识组
                            elif group == "标识" and "测试评语" in single_item and "标识" in single_item["测试评语"]:
                                # 确保物理状态字段存在
                                if "物理状态" not in single_item and states and len(states) > 0:
                                    single_item["物理状态"] = states[0]["物理状态"]
                                # 从评语中提取标识信息
                                single_item["物理状态值"] = single_item["测试评语"]
                                batch_results.append(single_item)
                                self.logger.debug(f"从评语中提取标识工艺成功: {single_item['物理状态值']}")
                except Exception as e:
                    self.logger.error(f"解析单个状态JSON失败: {e}")
        else:
            try:
                items = json.loads(json_str)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            # 确保物理状态组一致
                            if "物理状态组" in item:
                                if item["物理状态组"] != group:
                                    # 跳过不匹配的物理状态组，而不是强制修改
                                    self.logger.warning(f"跳过不匹配的物理状态组：{item['物理状态组']}（期望：{group}）")
                                    continue
                            else:
                                item["物理状态组"] = group
                            
                            # 检查物理状态是否在当前组的状态列表中
                            if "物理状态" in item:
                                state_valid = False
                                for state_info in states:
                                    if item["物理状态"] == state_info["物理状态"]:
                                        state_valid = True
                                        break
                                
                                if not state_valid:
                                    self.logger.warning(f"跳过无效的物理状态：{item['物理状态']}，不在当前组的状态列表中")
                                    continue
                                
                            # 检查物理状态值是否存在
                            if "物理状态值" in item and item["物理状态值"] != "文中未提及":
                                # 确保物理状态字段存在
                                if "物理状态" not in item:
                                    # 尝试从模型输出和states列表中推断
                                    for state_info in states:
                                        state_name = state_info["物理状态"]
                                        # 检查任何值中是否包含该状态名称
                                        for value in item.values():
                                            if isinstance(value, str) and state_name in value:
                                                item["物理状态"] = state_name
                                                self.logger.info(f"从内容中推断物理状态: {state_name}")
                                                break
                                        if "物理状态" in item:
                                            break
                                            
                                    # 如果仍未找到，使用默认值
                                    if "物理状态" not in item:
                                        if "第一个物理状态名称" in str(item):
                                            # 这可能是模型直接返回了模板，尝试关联到实际状态
                                            if states and len(states) > 0:
                                                item["物理状态"] = states[0]["物理状态"]
                                                self.logger.warning(f"模型返回了模板，使用第一个状态: {item['物理状态']}")
                                            else:
                                                item["物理状态"] = "未知状态"
                                        else:
                                            item["物理状态"] = "未知状态"
                                            
                                batch_results.append(item)
                                self.logger.debug(f"成功提取结果: {item.get('物理状态', '未知')} - {item['物理状态值']}")
                            # 特殊处理标识组
                            elif group == "标识" and "测试评语" in item and "标识" in item["测试评语"]:
                                # 确保物理状态字段存在
                                if "物理状态" not in item and states and len(states) > 0:
                                    item["物理状态"] = states[0]["物理状态"]
                                # 从评语中提取标识信息
                                item["物理状态值"] = item["测试评语"]
                                batch_results.append(item)
                                self.logger.debug(f"从评语中提取标识工艺成功: {item['物理状态值']}")
                else:
                    self.logger.warning(f"JSON不是数组格式: {json_str[:100]}...")
            except Exception as e:
                self.logger.error(f"解析JSON数组失败: {e}")
        
        # 如果仍然失败，尝试逐个处理
        if not batch_results:
            self.logger.warning(f"提取批次结果失败，尝试逐个处理物理状态组 '{group}' 的状态")
            for state_item in states:
                state = state_item['物理状态']
                # 直接处理单个状态
                single_prompt = f"""请从以下文本中提取关于"{group}"的"{state}"的具体物理状态值、风险评价和测试评语信息。

【重要！物理状态名称严格限制】
请确保返回的"物理状态"字段值必须为："{state}"，不要使用试验项目名称或其他值。

【风险评价判断标准】
- "可用"：描述中包含"常规结构"、"无可靠性隐患"、"工艺良好"、"满足宇航应用要求"等正面评价
- "限用"：描述中包含"存在风险"、"限制条件使用"、"建议评估后使用"等条件性评价
- "禁用"：描述中包含"不适合宇航应用"、"有可靠性隐患"、"不满足标准要求"等否定性评价

返回格式：
{{
    "物理状态组": "{group}",
    "物理状态": "{state}",
    "试验项目": "从文本中提取的试验项目",
    "物理状态值": "从文本中提取的物理状态值",
    "风险评价": "可用/限用/禁用（从文本判断）",
    "测试评语": "从文本中提取的简洁测试评价"
}}

如果文本中确实没有相关信息，请在"物理状态值"字段中填写"文中未提及"。

文本内容：
"""
                
                # 限制文本长度，避免超出模型的处理能力
                max_text_length = 8000  # 单独处理时使用更小的文本长度
                if len(text) > max_text_length:
                    text_front = text[:max_text_length//2]
                    text_back = text[-max_text_length//2:]
                    truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
                    single_prompt += truncated_text
                else:
                    single_prompt += text
                
                # 调用API
                single_result = self._call_llm_api(single_prompt)
                
                # 提取JSON
                json_str = self._extract_json_from_response(single_result)
                if json_str:
                    try:
                        single_item = json.loads(json_str)
                        if isinstance(single_item, dict):
                            # 确保必需字段存在
                            if "物理状态组" not in single_item:
                                single_item["物理状态组"] = group
                            
                            # 确保物理状态字段正确
                            if "物理状态" not in single_item or single_item["物理状态"] != state:
                                self.logger.warning(f"物理状态名称错误或缺失，修正为: {state}")
                                single_item["物理状态"] = state
                                
                            if "物理状态值" in single_item and single_item["物理状态值"] != "文中未提及":
                                batch_results.append(single_item)
                                self.logger.debug(f"单独处理成功: {single_item['物理状态']} - {single_item['物理状态值']}")
                            else:
                                # 特殊处理标识组
                                if group == "标识" and "测试评语" in single_item and "标识" in single_item["测试评语"]:
                                    # 从评语中提取标识信息
                                    single_item["物理状态值"] = single_item["测试评语"]
                                    batch_results.append(single_item)
                                    self.logger.debug(f"从评语中提取标识工艺成功: {single_item['物理状态值']}")
                    except Exception as e:
                        self.logger.error(f"解析单个状态JSON失败: {e}")
        
        if not batch_results:
            self.logger.warning(f"未能从批处理响应中提取任何有效结果")
            # 记录响应的前200个字符，便于调试
            self.logger.debug(f"响应内容: {result[:200]}...")
        
        return batch_results
    
    def extract_from_text(self, text, output_dir=None, output_json=False, output_excel=False, batch=True, max_workers=4, batch_by_group=True, filename='text_extraction'):
        """
        直接从文本内容提取信息
        
        参数:
            text: 要分析的文本内容
            output_dir: 输出目录，默认为None（如果需要保存）
            output_json: 是否输出JSON文件
            output_excel: 是否输出Excel文件
            batch: 是否使用批量处理方式
            max_workers: 批量处理时的最大并行工作线程数
            batch_by_group: 批量处理时是否按物理状态组进行批处理
            filename: 如果输出文件，使用的文件名前缀
            
        返回:
            提取的结果列表
        """
        self.logger.info(f"开始从文本内容提取信息 (长度: {len(text)} 字符)")
        
        # 检查文本是否为空
        if not text.strip():
            self.logger.error("文本内容为空")
            return []
        
        # 阶段1: 识别物理状态组和物理状态
        identified_states = self._extract_groups_and_states(text)
        
        # 如果未识别出任何物理状态，尝试备用方法
        if not identified_states:
            self.logger.warning("未识别出任何物理状态组合，尝试备用提取方法...")
            identified_states = self._extract_groups_and_states(text, use_simplified_prompt=True)
        
        # 阶段2: 提取具体值
        extraction_results = self._extract_specific_values(
            text, 
            identified_states, 
            parallel=True, 
            max_workers=max_workers, 
            batch=batch, 
            batch_by_group=batch_by_group
        )
        
        # 标准化结果
        standardized_results = self._standardize_results(extraction_results)
        
        # 如果需要输出文件
        if (output_json or output_excel) and output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存结果
            if standardized_results:
                if output_json:
                    json_output_file = os.path.join(output_dir, f"{filename}.json")
                    with open(json_output_file, 'w', encoding='utf-8') as f:
                        json.dump(standardized_results, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"JSON结果已保存到: {json_output_file}")
                
                if output_excel:
                    excel_output_file = os.path.join(output_dir, f"{filename}.xlsx")
                    df = pd.DataFrame(standardized_results)
                    df.to_excel(excel_output_file, index=False)
                    self.logger.info(f"Excel结果已保存到: {excel_output_file}")
            else:
                self.logger.warning("未提取到任何结果，未生成输出文件")
        
        self.logger.info("文本内容处理完成")
        return standardized_results