import json
import logging
import concurrent.futures

from ..llm_service import LLMService
from .prompts import EXTRACTION_GUIDELINES, EXTRACTION_SINGLE_PROMPT, EXTRACTION_BATCH_PROMPT


class ExtractionAgent:
    """
    提取Agent - 负责从文档中提取物理状态的具体值

    该Agent专注于:
    1. 根据IdentificationAgent识别的物理状态组和物理状态，提取具体的物理状态值
    2. 提取风险评价和测试评语
    3. 处理批量提取请求
    4. 支持并行处理以提高效率
    """

    def __init__(self, llm_service, debug=False):
        """
        初始化提取Agent

        参数:
            llm_service: LLMService实例，用于调用大语言模型
            debug: 是否启用调试模式
        """
        self.llm_service = llm_service
        self.debug = debug
        self.max_text_length = 20000  # 根据模型能力调整，避免超过模型的token限制
        
        # 配置日志
        self.logger = self._setup_logger(debug)
        
        self.logger.info("初始化ExtractionAgent...")
        self.logger.info("ExtractionAgent初始化完成。")
    
    def _setup_logger(self, debug):
        """设置日志记录器"""
        logger = logging.getLogger("ExtractionAgent")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO if not debug else logging.DEBUG)
        return logger

    def extract_specific_values(self, text, identified_states, parallel=True, max_workers=4, batch=False,
                                batch_by_group=True):
        """
        提取具体的物理状态值，支持并行处理和批处理

        参数:
            text: 文档文本内容
            identified_states: 识别出的物理状态组合列表
            parallel: 是否使用并行处理
            max_workers: 并行处理时的最大工作线程数
            batch: 是否使用批处理模式
            batch_by_group: 批处理模式下是否按物理状态组分组

        返回:
            提取结果的列表
        """
        # 记录处理模式
        self._log_processing_mode(batch, parallel, max_workers, batch_by_group)
        
        # 检查输入有效性
        if not identified_states:
            self.logger.warning("没有识别出物理状态组合，无法提取具体值")
            return []
        
        # 根据处理模式选择不同的提取策略
        if batch:
            return self._process_in_batch_mode(text, identified_states, parallel, max_workers, batch_by_group)
        else:
            return self._process_individual_items(text, identified_states, parallel, max_workers)

    def _log_processing_mode(self, batch, parallel, max_workers, batch_by_group):
        """记录处理模式信息"""
        if batch:
            self.logger.info(f"正在批量提取具体的物理状态值（最大并行数：{max_workers}，按组批处理：{batch_by_group}）...")
        elif parallel:
            self.logger.info(f"正在并行提取具体的物理状态值（最大并行数：{max_workers}）...")
        else:
            self.logger.info("正在提取具体的物理状态值...")

    def _process_in_batch_mode(self, text, identified_states, parallel, max_workers, batch_by_group):
        """批处理模式下的处理逻辑"""
        results = []
        
        if batch_by_group:
            # 按物理状态组分组批处理
            return self._process_by_group(text, identified_states, parallel, max_workers)
        else:
            # 固定批次大小批处理
            return self._process_by_fixed_batch_size(text, identified_states)
    
    def _process_by_group(self, text, identified_states, parallel, max_workers):
        """按物理状态组进行分组批处理"""
        results = []
        
        # 按物理状态组分组
        groups = self._group_states_by_group(identified_states)
        
        # 创建任务列表
        tasks = [(group, states) for group, states in groups.items()]
        
        # 处理各个批次
        if parallel and max_workers > 1:
            # 并行处理各个批次
            results = self._process_batches_in_parallel(text, tasks, max_workers)
        else:
            # 串行处理各个批次
            results = self._process_batches_sequentially(text, tasks)
            
        return results
    
    def _group_states_by_group(self, identified_states):
        """将物理状态按物理状态组分组"""
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
        
        return groups
    
    def _process_batches_in_parallel(self, text, tasks, max_workers):
        """并行处理批次任务"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_group = {
                executor.submit(self._process_single_batch, text, group, states): group
                for group, states in tasks
            }

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
        
        return results
    
    def _process_batches_sequentially(self, text, tasks):
        """串行处理批次任务"""
        results = []
        
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
        
        return results
    
    def _process_by_fixed_batch_size(self, text, identified_states, batch_size=3):
        """按固定批次大小处理数据"""
        results = []
        total_items = len(identified_states)
        num_batches = (total_items + batch_size - 1) // batch_size

        self.logger.info(f"将{total_items}个物理状态组合分为{num_batches}个批次处理（每批{batch_size}个）")

        for i in range(0, total_items, batch_size):
            batch = identified_states[i:i + batch_size]

            for item in batch:
                group = item['物理状态组']
                states = [item]

                try:
                    batch_results = self._process_single_batch(text, group, states)
                    if batch_results:
                        results.extend(batch_results)
                except Exception as e:
                    self.logger.error(f"处理物理状态组 '{group}' 时出错: {e}")
        
        return results
    
    def _process_individual_items(self, text, identified_states, parallel, max_workers):
        """处理单个物理状态项目（非批处理模式）"""
        results = []
        
        if parallel and max_workers > 1:
            # 并行处理
            results = self._process_items_in_parallel(text, identified_states, max_workers)
        else:
            # 串行处理
            results = self._process_items_sequentially(text, identified_states)
        
        return results
    
    def _process_items_in_parallel(self, text, identified_states, max_workers):
        """并行处理单个物理状态项目"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self._process_single_item, text, item): item 
                for item in identified_states
            }

            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(
                        f"处理物理状态组合 '{item['物理状态组']}-{item['物理状态']}' 时出错: {e}")
        
        return results
    
    def _process_items_sequentially(self, text, identified_states):
        """串行处理单个物理状态项目"""
        results = []
        
        for item in identified_states:
            try:
                result = self._process_single_item(text, item)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"处理物理状态组合 '{item['物理状态组']}-{item['物理状态']}' 时出错: {e}")
        
        return results
    
    def _process_single_item(self, text, item):
        """处理单个物理状态组合"""
        group = item['物理状态组']
        state = item['物理状态']

        # 构建提示
        prompt = EXTRACTION_SINGLE_PROMPT.format(
            EXTRACTION_GUIDELINES=EXTRACTION_GUIDELINES,
            group=group,
            state=state
        ) + text

        # 检查文本长度
        self._check_text_length(prompt)

        # 调试日志
        if self.debug:
            self.logger.debug(f"使用的提示模板: {prompt[:200]}...")

        # 调用LLM API
        result = self.llm_service.call_llm(prompt)

        if not result:
            self.logger.warning(f"API返回空响应，跳过物理状态 '{group}-{state}'")
            return None

        # 从结果中提取JSON部分
        json_str = self.llm_service.extract_json_from_response(result)

        if not json_str:
            self.logger.warning(f"无法从API响应中提取JSON，跳过物理状态 '{group}-{state}'")
            return None

        # 解析并验证JSON
        return self._parse_and_validate_single_result(json_str, group, state)
    
    def _check_text_length(self, text):
        """检查文本长度是否超出限制"""
        if len(text) > self.max_text_length:
            raise ValueError(f"文本长度超出限制: 最大允许长度为{self.max_text_length}字符")
    
    def _parse_and_validate_single_result(self, json_str, group, state):
        """解析和验证单个提取结果"""
        try:
            # 解析JSON
            data = json.loads(json_str)

            # 验证结果是否符合预期
            return self._validate_and_fix_result(data, group, state)
        except Exception as e:
            self.logger.error(f"解析API响应失败: {e}")
            return None
    
    def _validate_and_fix_result(self, data, group, state):
        """验证提取结果并修复缺失字段"""
        expected_keys = ["物理状态组", "物理状态", "试验项目", "物理状态值", "风险评价", "测试评语"]
        
        if not all(key in data for key in expected_keys):
            missing_keys = [key for key in expected_keys if key not in data]
            self.logger.warning(f"响应中缺少必要字段: {missing_keys}")

            # 添加缺失的字段
            for key in missing_keys:
                if key == "物理状态组":
                    data[key] = group
                elif key == "物理状态":
                    data[key] = state
                else:
                    data[key] = "文中未提及" if key == "物理状态值" else "文档中未包含此信息"

        return data

    def _process_single_batch(self, text, group, states):
        """
        处理单个批次的状态组合
        
        参数:
            text: 文档文本内容
            group: 物理状态组名称
            states: 该组下的物理状态列表
            
        返回:
            提取结果列表
        """
        # 生成批处理提示
        prompt = self._generate_batch_prompt(text, group, states)
        
        # 检查文本长度
        self._check_text_length(prompt)
        
        # 调试日志
        if self.debug:
            self.logger.debug(f"使用的提示模板: {prompt[:200]}...")

        # 调用LLM API
        result = self.llm_service.call_llm(prompt)

        if not result:
            self.logger.warning(f"API返回空响应，跳过物理状态组 '{group}'")
            return []

        # 解析结果
        batch_results = self._parse_batch_results(result, group)
        
        # 检查结果完整性并补充缺失状态
        return self._check_and_fill_missing_states(batch_results, group, states)
    
    def _generate_batch_prompt(self, text, group, states):
        """生成批处理提示"""
        # 每个状态准备一个简单的描述
        states_str = "\n".join([f"- {state['物理状态']}" for state in states])
        
        # 构建提示
        return EXTRACTION_BATCH_PROMPT.format(
            EXTRACTION_GUIDELINES=EXTRACTION_GUIDELINES, 
            group=group, 
            states_str=states_str
        ) + text
    
    def _parse_batch_results(self, result, group):
        """解析批处理结果"""
        batch_results = []
        
        # 先尝试解析为JSON数组
        json_str = self.llm_service.extract_json_from_response(result, is_array=True)
        
        if json_str:
            # 解析JSON数组
            batch_results = self._parse_json_array(json_str, group)
        else:
            # 尝试解析单个JSON对象
            self.logger.warning(f"无法从批处理响应中提取JSON数组，尝试查找单个JSON对象")
            batch_results = self._parse_single_json_object(result, group)
            
        return batch_results
    
    def _parse_json_array(self, json_str, group):
        """解析JSON数组格式的结果"""
        batch_results = []
        
        try:
            items = json.loads(json_str)
            if isinstance(items, list):
                # 验证每个项是否属于当前组
                for item in items:
                    if isinstance(item, dict) and "物理状态组" in item:
                        if item["物理状态组"] == group:
                            batch_results.append(item)
                        else:
                            self.logger.warning(f"跳过不匹配的物理状态组：{item['物理状态组']}（期望：{group}）")
                    else:
                        self.logger.warning("提取的JSON数组包含无效项或缺少'物理状态组'字段")
            else:
                self.logger.warning("提取的JSON不是有效的数组")
        except Exception as e:
            self.logger.error(f"解析JSON数组失败: {e}")
            
        return batch_results
    
    def _parse_single_json_object(self, result, group):
        """解析单个JSON对象格式的结果"""
        batch_results = []
        
        json_str = self.llm_service.extract_json_from_response(result)
        if json_str:
            try:
                single_item = json.loads(json_str)
                if isinstance(single_item, dict):
                    # 确保物理状态组一致
                    if "物理状态组" in single_item:
                        if single_item["物理状态组"] == group:
                            # 把单个项目包装成数组
                            batch_results = [single_item]
                        else:
                            # 不匹配时，记录并返回空结果
                            self.logger.warning(f"跳过不匹配的物理状态组：{single_item['物理状态组']}（期望：{group}）")
                    else:
                        self.logger.warning("提取的JSON对象缺少'物理状态组'字段")
                else:
                    self.logger.warning("提取的JSON不是有效的对象")
            except Exception as e:
                self.logger.error(f"解析单个JSON对象失败: {e}")
                
        return batch_results
    
    def _check_and_fill_missing_states(self, batch_results, group, states):
        """检查结果完整性并补充缺失的状态"""
        # 检查是否成功提取
        if not batch_results:
            self.logger.warning(f"未能从物理状态组 '{group}' 提取到有效结果")
            return batch_results
        
        self.logger.info(f"从物理状态组 '{group}' 提取到 {len(batch_results)} 个结果")

        # 检查结果是否完整
        expected_states = {state['物理状态'] for state in states}
        extracted_states = {item['物理状态'] for item in batch_results if '物理状态' in item}
        missing_states = expected_states - extracted_states

        if missing_states:
            self.logger.warning(f"物理状态组 '{group}' 中有未提取到的状态: {missing_states}")

            # 为缺失的状态创建默认项
            for missing in missing_states:
                default_item = self._create_default_item(group, missing)
                batch_results.append(default_item)

        return batch_results
    
    def _create_default_item(self, group, state):
        """创建默认的状态项目"""
        return {
            "物理状态组": group,
            "物理状态": state,
            "试验项目": "文中未提及",
            "物理状态值": "文中未提及",
            "风险评价": "可用",  # 默认风险评价
            "测试评语": "文档中未包含此信息"
        }