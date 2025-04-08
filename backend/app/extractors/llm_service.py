import json
import requests
import logging
import time
import random
import traceback
import sys
import re

class LLMService:
    """LLM API服务类，处理与不同LLM API的通信"""
    
    def __init__(self, model_name="gpt-3.5-turbo", server_ip="127.0.0.1", server_port=8000, 
                 api_key=None, api_base=None, debug=False, use_api=None):
        """
        初始化LLM服务
        
        参数:
            model_name: 使用的模型名称
            server_ip: API服务器IP地址（本地服务时使用）
            server_port: API服务器端口（本地服务时使用）
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
        self.logger = logging.getLogger("LLMService")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)
        
        self.logger.info("初始化LLMService...")
        if self.use_cloud_api:
            self.logger.info(f"使用云API模式，模型: {self.model_name}")
        else:
            self.logger.info(f"使用本地API模式，服务器: {self.server_ip}:{self.server_port}")
    
    def call_llm(self, prompt, max_retries=3, retry_delay=2):
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
    
    def extract_json_from_response(self, response, is_array=False):
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
            obj_json = self.extract_json_from_response(response, is_array=False)
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
                array_json = self.extract_json_from_response(response, is_array=True)
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
    
    def _save_intermediate_result(self, identifier, data):
        """保存中间结果到文件（用于调试）"""
        if hasattr(self, 'intermediate_dir'):
            import os
            import json
            
            os.makedirs(self.intermediate_dir, exist_ok=True)
            file_path = os.path.join(self.intermediate_dir, f"{identifier}.json")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.warning(f"保存中间结果失败: {str(e)}") 