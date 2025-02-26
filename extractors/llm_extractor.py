import os
import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Union
from .base_extractor import BaseExtractor

# 尝试导入LangChain相关库
try:
    from langchain.llms import HuggingFacePipeline
    from langchain.chat_models import ChatOpenAI
    from langchain.prompts.chat import ChatPromptTemplate, HumanMessage, SystemMessage
    from langchain.chains import LLMChain
    from langchain.callbacks import AsyncIteratorCallbackHandler
    from transformers import AutoTokenizer, AutoModel, pipeline
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("警告: 无法导入LangChain相关库，将使用模拟模式")
    LANGCHAIN_AVAILABLE = False

class LLMExtractor(BaseExtractor):
    """基于大型语言模型的信息抽取器"""
    
    def __init__(self, model_name="THUDM/chatglm3-6b", use_api=False, api_key=None, temperature=0.01, max_tokens=4096):
        """
        初始化LLM抽取器
        
        参数:
            model_name: 模型名称或路径
            use_api: 是否使用API（如OpenAI API）
            api_key: API密钥（当use_api=True时需要）
            temperature: 温度参数，控制生成的随机性
            max_tokens: 最大生成token数
        """
        self.model_name = model_name
        self.use_api = use_api
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = None
        
        # 加载停用词和专有名词
        self.stopwords = self.load_stopwords()
        self.proper_nouns = self.load_proper_nouns()
        
        print(f"初始化LLM模型: {model_name}")
        
        # 如果LangChain可用，尝试加载模型
        if LANGCHAIN_AVAILABLE:
            if use_api:
                # 使用API（如OpenAI）
                if "gpt" in model_name.lower():
                    if not api_key and "OPENAI_API_KEY" not in os.environ:
                        print("警告: 使用OpenAI API需要提供api_key或设置OPENAI_API_KEY环境变量")
                    elif api_key:
                        os.environ["OPENAI_API_KEY"] = api_key
                    
                    try:
                        self.model = ChatOpenAI(
                            model_name=model_name,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        print(f"成功加载OpenAI API模型: {model_name}")
                    except Exception as e:
                        print(f"加载OpenAI API模型失败: {e}")
                else:
                    print(f"警告: 不支持的API模型: {model_name}")
            else:
                # 使用本地模型
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
                    self.model_instance = AutoModel.from_pretrained(model_name, trust_remote_code=True)
                    
                    # 创建HuggingFace pipeline
                    text_generation_pipeline = pipeline(
                        "text-generation",
                        model=self.model_instance,
                        tokenizer=self.tokenizer,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        trust_remote_code=True
                    )
                    
                    # 创建LangChain LLM
                    self.model = HuggingFacePipeline(pipeline=text_generation_pipeline)
                    print(f"成功加载本地模型: {model_name}")
                except Exception as e:
                    print(f"加载本地模型失败: {e}")
                    print("将使用模拟模式...")
        else:
            print("警告: LangChain库不可用，将使用模拟模式")
    
    def load_stopwords(self):
        """加载停用词列表"""
        stopwords = set()
        try:
            stopwords_path = os.path.join("data", "nlp_static", "stopwords.txt")
            if os.path.exists(stopwords_path):
                with open(stopwords_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            stopwords.add(word)
                print(f"成功加载 {len(stopwords)} 个停用词")
            else:
                print(f"停用词文件不存在: {stopwords_path}")
        except Exception as e:
            print(f"加载停用词失败: {e}")
        return stopwords
    
    def load_proper_nouns(self):
        """加载专有名词词典"""
        proper_nouns = set()
        try:
            proper_nouns_path = os.path.join("data", "nlp_static", "proper_nouns.txt")
            if os.path.exists(proper_nouns_path):
                with open(proper_nouns_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            proper_nouns.add(word)
                print(f"成功加载 {len(proper_nouns)} 个专有名词")
            else:
                print(f"专有名词文件不存在: {proper_nouns_path}")
        except Exception as e:
            print(f"加载专有名词失败: {e}")
        return proper_nouns
    
    def preprocess_text(self, text):
        """
        预处理文本，包括去除停用词等
        
        参数:
            text: 待处理的文本
            
        返回:
            处理后的文本
        """
        # 如果没有加载停用词，直接返回原文本
        if not self.stopwords:
            return text
            
        # 对于中文文本，需要先进行分词
        # 这里使用简单的字符级处理
        processed_chars = []
        for char in text:
            if char not in self.stopwords:
                processed_chars.append(char)
        
        return ''.join(processed_chars)
    
    def identify_entities(self, text):
        """
        识别文本中的实体（如专有名词）
        
        参数:
            text: 待处理的文本
            
        返回:
            识别出的实体列表
        """
        entities = []
        
        # 如果没有加载专有名词，返回空列表
        if not self.proper_nouns:
            return entities
            
        # 简单的字符串匹配查找专有名词
        for noun in self.proper_nouns:
            if noun in text:
                entities.append(noun)
                
        return entities
    
    def generate_prompt(self, text, section_type):
        """根据章节类型生成不同的提示"""
        prompts = {
            "标识部分": f"""
从以下文本中提取器件标识相关信息，包括：型号规格、生产批次、生产厂标识、标识方式、
标识牢固度以及问题与建议。以JSON格式返回。

文本内容：
{text}
            """,
            
            "封装结构": f"""
从以下文本中提取器件封装结构相关信息，包括：封装类型、封装材料、封装工艺、
工艺质量评估。以JSON格式返回。

文本内容：
{text}
            """,
            
            "芯片": f"""
从以下文本中提取芯片相关信息，包括：芯片装配结构、芯片粘接材料、芯片安装工艺、
芯片结构和工艺。以JSON格式返回。

文本内容：
{text}
            """,
            
            "键合系统": f"""
从以下文本中提取键合系统相关信息，包括：键合结构、键合丝材料与工艺、
键合质量评估。以JSON格式返回。

文本内容：
{text}
            """,
            
            "三、详细分析": f"""
从以下文本中提取器件的详细分析信息，包括：型号规格、生产批次、生产厂标识、
封装类型、封装材料、芯片类型、键合信息等。以JSON格式返回。

文本内容：
{text}
            """,
            
            "四、附图": f"""
从以下文本中提取附图中可能包含的关键信息，包括：图片描述、图片内容、
图片中显示的器件特征等。以JSON格式返回。

文本内容：
{text}
            """
        }
        
        # 获取对应提示，如果没有则使用通用提示
        return prompts.get(section_type, f"""
从以下文本中提取关键技术信息，以JSON格式返回。

文本内容：
{text}
        """)
    
    def extract_info(self, text, section_type):
        """使用LLM提取信息"""
        # 预处理文本
        preprocessed_text = self.preprocess_text(text)
        
        # 识别实体
        entities = self.identify_entities(text)
        
        # 生成提示，包含识别出的实体信息
        prompt = self.generate_prompt(text, section_type)
        if entities:
            entity_info = "文本中识别出的重要实体: " + ", ".join(entities[:10])  # 限制实体数量
            prompt = prompt + "\n\n" + entity_info
        
        print(f"发送提示到LLM模型，提取\"{section_type}\"信息")
        
        # 如果模型已加载，使用模型生成
        if self.model and LANGCHAIN_AVAILABLE:
            try:
                if self.use_api and "gpt" in self.model_name.lower():
                    # 使用ChatOpenAI
                    chat_prompt = ChatPromptTemplate.from_messages([
                        SystemMessage(content="你是一个专业的器件信息提取助手，擅长从文本中提取结构化信息。"),
                        HumanMessage(content=prompt)
                    ])
                    chain = LLMChain(prompt=chat_prompt, llm=self.model)
                    response = chain.run("")
                else:
                    # 使用本地模型
                    response = self.model(prompt)
                
                # 清理输出
                response = self.clean_output(response)
                
                # 解析JSON
                try:
                    result = json.loads(response)
                    # 优化结果
                    return self.optimize_result(result, text)
                except json.JSONDecodeError:
                    print(f"无法解析JSON: {response}")
                    # 尝试提取JSON部分
                    json_match = re.search(r'({[\s\S]*})', response)
                    if json_match:
                        try:
                            result = json.loads(json_match.group(1))
                            return self.optimize_result(result, text)
                        except:
                            pass
                    
                    # 如果仍然失败，返回原始响应
                    return {"extracted_text": response}
            
            except Exception as e:
                print(f"LLM调用出错: {e}")
                # 出错时使用模拟数据
                print("使用正则表达式提取数据...")
                return self.get_mock_data(section_type, text)
        else:
            # 模型未加载，使用模拟数据
            print("使用正则表达式提取数据...")
            return self.get_mock_data(section_type, text)
    
    async def extract_info_async(self, text, section_type):
        """异步使用LLM提取信息"""
        if not LANGCHAIN_AVAILABLE:
            return self.extract_info(text, section_type)
            
        prompt = self.generate_prompt(text, section_type)
        
        print(f"异步发送提示到LLM模型，提取\"{section_type}\"信息")
        
        # 如果模型已加载且支持异步调用
        if self.model and self.use_api and "gpt" in self.model_name.lower():
            try:
                callback = AsyncIteratorCallbackHandler()
                
                # 创建异步模型
                async_model = ChatOpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    callbacks=[callback]
                )
                
                # 创建提示
                chat_prompt = ChatPromptTemplate.from_messages([
                    ChatMessage(role="system", content="你是一个专业的器件信息提取助手，擅长从文本中提取结构化信息。"),
                    ChatMessage(role="user", content=prompt)
                ])
                
                # 创建链
                chain = LLMChain(prompt=chat_prompt, llm=async_model)
                
                # 启动异步任务
                task = asyncio.create_task(chain.arun(""))
                
                # 收集响应
                response = ""
                async for token in callback.aiter():
                    response += token
                
                await task
                
                # 清理输出
                response = self.clean_output(response)
                
                # 解析JSON
                try:
                    result = json.loads(response)
                    return self.optimize_result(result, text)
                except json.JSONDecodeError:
                    # 尝试提取JSON部分
                    json_match = re.search(r'({[\s\S]*})', response)
                    if json_match:
                        try:
                            result = json.loads(json_match.group(1))
                            return self.optimize_result(result, text)
                        except:
                            pass
                    
                    # 如果仍然失败，返回原始响应
                    return {"extracted_text": response}
            
            except Exception as e:
                print(f"异步LLM调用出错: {e}")
                # 出错时使用模拟数据
                return self.get_mock_data(section_type)
        else:
            # 不支持异步或模型未加载，使用同步方法
            return self.extract_info(text, section_type)
    
    def clean_output(self, output):
        """清理LLM输出"""
        # 去除特殊标记
        unwanted_phrases = ["<|endoftext|>", "<|im_end|>"]
        for phrase in unwanted_phrases:
            if isinstance(output, str) and phrase in output:
                output = output.replace(phrase, "")
        
        # 提取JSON部分
        if isinstance(output, str) and output.find('{') != -1:
            start = output.find('{')
            end = output.rfind('}') + 1
            if end > start:
                output = output[start:end]
        
        return output.strip()
    
    def get_mock_data(self, section_type, text=None):
        """获取模拟数据，如果提供了文本，尝试从文本中提取信息"""
        # 如果提供了文本，尝试简单提取
        if text:
            if "标识部分" in section_type:
                result = {}
                # 简单的正则匹配提取
                type_match = re.search(r'型号规格为(\w+)', text)
                if type_match:
                    result["型号规格"] = type_match.group(1)
                
                batch_match = re.search(r'生产批次为([\w-]+)', text)
                if batch_match:
                    result["生产批次"] = batch_match.group(1)
                
                manufacturer_match = re.search(r'生产厂标识为([\w\s]+)[。，]', text)
                if manufacturer_match:
                    result["生产厂标识"] = manufacturer_match.group(1).strip()
                
                mark_method_match = re.search(r'标识采用(\w+)方式', text)
                if mark_method_match:
                    result["标识方式"] = mark_method_match.group(1)
                
                firmness_match = re.search(r'标识牢固度(\w+)', text)
                if firmness_match:
                    result["标识牢固度"] = firmness_match.group(1)
                
                # 提取问题与建议
                problems = []
                for problem in re.finditer(r'[：:](缺少[^，。]+|建议[^，。]+)[，。]', text):
                    problems.append(problem.group(1))
                
                if problems:
                    result["问题与建议"] = problems
                
                # 如果提取到了信息，返回结果
                if result:
                    return result
            
            elif "封装结构" in section_type:
                result = {}
                # 提取封装类型
                package_match = re.search(r'采用(\w+\d+\w+)封装', text)
                if package_match:
                    result["封装类型"] = package_match.group(1)
                
                # 提取封装材料
                materials = []
                materials_match = re.search(r'封装材料[主要]*包括([\w\s、/]+)[。，]', text)
                if materials_match:
                    materials_text = materials_match.group(1)
                    materials = [m.strip() for m in re.split(r'[、和]', materials_text) if m.strip()]
                
                if materials:
                    result["封装材料"] = materials
                
                # 提取封装工艺
                process_match = re.search(r'封装工艺采用([\w]+工艺)', text)
                if process_match:
                    result["封装工艺"] = process_match.group(1)
                
                # 提取质量评估
                quality_match = re.search(r'质量评估[为是]([\w]+)', text)
                if quality_match:
                    result["质量评估"] = quality_match.group(1)
                
                # 如果提取到了信息，返回结果
                if result:
                    return result
            
            elif "芯片" in section_type:
                result = {}
                # 提取芯片装配结构
                structure_match = re.search(r'芯片装配结构为([\w]+结构)', text)
                if structure_match:
                    result["芯片装配结构"] = structure_match.group(1)
                
                # 提取芯片粘接材料
                material_match = re.search(r'芯片粘接材料为([\w]+)', text)
                if material_match:
                    result["芯片粘接材料"] = material_match.group(1)
                
                # 提取芯片安装工艺
                process_match = re.search(r'芯片安装工艺采用([\w]+工艺)', text)
                if process_match:
                    result["芯片安装工艺"] = process_match.group(1)
                
                # 提取芯片结构和工艺
                tech_match = re.search(r'芯片结构采用([\w]+工艺)', text)
                if tech_match:
                    result["芯片结构和工艺"] = tech_match.group(1)
                
                # 如果提取到了信息，返回结果
                if result:
                    return result
        
        # 如果没有提供文本或提取失败，返回默认模拟数据
        if "标识部分" in section_type:
            return {
                "型号规格": "9288RH",
                "生产批次": "1440",
                "生产厂标识": "B",
                "标识方式": "油墨印刷",
                "标识牢固度": "良好",
                "问题与建议": ["缺少静电敏感度标识信息", "建议在管壳正面增加管脚定位标识"]
            }
        elif "封装结构" in section_type:
            return {
                "封装类型": "CQFP48陶瓷封装",
                "封装材料": ["Au/Sn合金", "Fe/Ni合金", "CuAg焊料"],
                "封装工艺": "焊料环熔封密封工艺",
                "质量评估": "良好"
            }
        elif "三、详细分析" in section_type:
            return {
                "型号规格": "XC9536",
                "生产批次": "2023-A",
                "生产厂标识": "XilinxCorp",
                "封装类型": "PLCC44",
                "封装材料": ["环氧树脂", "铜引线框架"],
                "芯片类型": "CPLD",
                "芯片工艺": "CMOS工艺",
                "键合方式": "金线键合",
                "问题与建议": ["封装表面有轻微划痕", "建议改进标识清晰度"]
            }
        elif "四、附图" in section_type:
            return {
                "图片描述": "器件内部结构X射线照片",
                "图片内容": "显示了芯片、引线框架和键合连接",
                "器件特征": "可见芯片尺寸约为5mm×5mm，键合丝直径约为25μm",
                "问题与建议": ["建议提供更高分辨率的芯片表面照片"]
            }
        
        # 返回通用模拟数据
        return {"extracted_info": "模拟LLM提取结果"}
    
    def optimize_result(self, result, text):
        """
        优化提取结果
        
        参数:
            result: 提取的结果
            text: 原始文本
        
        返回:
            优化后的结果
        """
        optimized = result.copy()
        
        # 处理列表值
        for key, value in optimized.items():
            if isinstance(value, list):
                # 如果列表只有一个元素，转换为字符串
                if len(value) == 1:
                    optimized[key] = value[0]
        
        # 处理空值
        for key in list(optimized.keys()):
            if optimized[key] is None or optimized[key] == "" or optimized[key] == []:
                optimized[key] = "文中未提及"
        
        return optimized
    
    def extract_info_ensemble(self, text, section_type, models=None):
        """
        使用多个模型集成提取信息
        
        参数:
            text: 待提取的文本
            section_type: 章节类型
            models: 模型列表，如果为None则使用默认模型
        
        返回:
            集成后的提取结果
        """
        if not models or len(models) <= 1:
            # 使用单个默认模型
            return self.extract_info(text, section_type)
        
        # 使用多个模型提取
        results = []
        original_model_name = self.model_name
        original_model = self.model
        
        for model_name in models:
            # 临时切换模型
            self.model_name = model_name
            
            # 根据模型类型决定是否使用API
            use_api = "gpt" in model_name.lower()
            self.use_api = use_api
            
            # 重新初始化模型
            if LANGCHAIN_AVAILABLE:
                try:
                    if use_api:
                        self.model = ChatOpenAI(
                            model_name=model_name,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    else:
                        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
                        self.model_instance = AutoModel.from_pretrained(model_name, trust_remote_code=True)
                        
                        text_generation_pipeline = pipeline(
                            "text-generation",
                            model=self.model_instance,
                            tokenizer=self.tokenizer,
                            max_new_tokens=self.max_tokens,
                            temperature=self.temperature,
                            trust_remote_code=True
                        )
                        
                        self.model = HuggingFacePipeline(pipeline=text_generation_pipeline)
                except Exception as e:
                    print(f"加载模型 {model_name} 失败: {e}")
                    continue
            
            # 提取信息
            result = self.extract_info(text, section_type)
            results.append(result)
        
        # 恢复原始模型
        self.model_name = original_model_name
        self.model = original_model
        
        # 合并结果
        merged_result = self.merge_results(results)
        
        return merged_result
    
    def merge_results(self, results):
        """
        合并多个模型的提取结果
        
        参数:
            results: 多个模型的提取结果列表
        
        返回:
            合并后的结果
        """
        if not results:
            return {}
        
        # 如果只有一个结果，直接返回
        if len(results) == 1:
            return results[0]
        
        # 合并所有结果
        merged = {}
        all_keys = set()
        for result in results:
            all_keys.update(result.keys())
        
        for key in all_keys:
            values = []
            weights = []
            
            for i, result in enumerate(results):
                if key in result and result[key] != "文中未提及":
                    values.append(result[key])
                    # 给不同模型分配权重，可以根据模型性能调整
                    weights.append(1.0)
            
            if not values:
                merged[key] = "文中未提及"
            elif len(set(map(str, values))) == 1:
                # 所有模型结果一致
                merged[key] = values[0]
            else:
                # 使用加权投票
                value_scores = {}
                for value, weight in zip(values, weights):
                    value_str = str(value)
                    if value_str in value_scores:
                        value_scores[value_str] += weight
                    else:
                        value_scores[value_str] = weight
                
                # 选择得分最高的值
                best_value_str = max(value_scores, key=value_scores.get)
                
                # 转换回原始类型
                for value in values:
                    if str(value) == best_value_str:
                        merged[key] = value
                        break
        
        return merged
    
    def score_extraction_result(self, result, text):
        """
        评分提取结果的质量
        
        参数:
            result: 提取的结果
            text: 原始文本
        
        返回:
            评分和改进建议
        """
        # 计算结果完整性
        completeness = 0
        expected_fields = self.get_expected_fields(result)
        filled_fields = sum(1 for field in expected_fields if field in result and result[field] != "文中未提及")
        
        if expected_fields:
            completeness = filled_fields / len(expected_fields)
        
        # 计算结果一致性
        consistency = 1.0
        for field, value in result.items():
            if isinstance(value, str) and value != "文中未提及":
                # 检查文本中是否包含该值
                if value.lower() not in text.lower():
                    consistency -= 0.1
        
        # 确保一致性不小于0
        consistency = max(0, consistency)
        
        # 总分
        score = (completeness * 0.7) + (consistency * 0.3)
        
        # 改进建议
        suggestions = []
        if completeness < 0.5:
            suggestions.append("提取结果不完整，建议检查文本是否包含所需信息")
        if consistency < 0.7:
            suggestions.append("提取结果与原文一致性较低，建议检查提取逻辑")
        
        return {
            "score": score,
            "completeness": completeness,
            "consistency": consistency,
            "suggestions": suggestions
        }

    def get_expected_fields(self, result):
        """获取期望的字段列表"""
        # 根据结果类型确定期望字段
        if "型号规格" in result:
            return ["型号规格", "生产批次", "生产厂标识"]
        elif "封装类型" in result:
            return ["封装类型", "封装材料", "封装工艺"]
        elif "芯片类型" in result:
            return ["芯片类型", "芯片工艺"]
        elif "键合方式" in result:
            return ["键合方式"]
        
        # 默认返回空列表
        return [] 