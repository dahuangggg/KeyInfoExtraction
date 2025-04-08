import json
import logging
import concurrent.futures
from tqdm import tqdm

from ..llm_service import LLMService


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

        # 配置日志
        self.logger = logging.getLogger("ExtractionAgent")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)

        self.logger.info("初始化ExtractionAgent...")
        self.logger.info("ExtractionAgent初始化完成。")

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
        # 根据参数选择合适的处理模式
        if batch:
            self.logger.info(f"正在批量提取具体的物理状态值（最大并行数：{max_workers}，按组批处理：{batch_by_group}）...")
        elif parallel:
            self.logger.info(f"正在并行提取具体的物理状态值（最大并行数：{max_workers}）...")
        else:
            self.logger.info("正在提取具体的物理状态值...")

        if not identified_states:
            self.logger.warning("没有识别出物理状态组合，无法提取具体值")
            return []

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
                            future_to_group = {executor.submit(self._process_single_batch, text, group, states): group
                                               for group, states in tasks}

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

                        pbar.update(1)
        # 常规单个处理模式（串行或并行）
        else:
            total = len(identified_states)

            def process_item(item):
                """处理单个物理状态组合"""
                group = item['物理状态组']
                state = item['物理状态']

                # 构建提示
                prompt = f"""请从以下文本中提取关于"{group}"的"{state}"的具体物理状态值、风险评价和测试评语信息。

【试验项目指导】
试验项目通常包括以下关键词：
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

请重点关注与此相关的描述。

【风险评价判断标准】
分析风险评价时，请注意以下规则：
- "可用"：描述中包含"常规结构"、"无可靠性隐患"、"工艺良好"、"满足宇航应用要求"等正面评价
- "限用"：描述中包含"存在风险"、"限制条件使用"、"建议评估后使用"、"限进行处理措施后使用"等条件性评价
- "禁用"：描述中包含"不适合宇航应用"、"有可靠性隐患"、"不满足标准要求"、"超标"等否定性评价

【物理状态值标准化指南】
为确保提取的物理状态值符合标准格式，请参考以下表达映射：
- "{group}"-"{state}"的标准物理状态值范围包括常见行业表达
- 当文档描述类似时，应提取为对应的标准物理状态值

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
                    text_front = text[:max_text_length // 2]
                    text_back = text[-max_text_length // 2:]
                    truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
                    prompt += truncated_text
                else:
                    prompt += text

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

                try:
                    # 解析JSON
                    data = json.loads(json_str)

                    # 验证结果是否符合预期
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
                except Exception as e:
                    self.logger.error(f"解析API响应失败: {e}")
                    return None

            # 处理所有物理状态组合
            with tqdm(total=total, desc="处理物理状态组合") as pbar:
                if parallel and max_workers > 1:
                    # 并行处理
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_item = {executor.submit(process_item, item): item for item in identified_states}

                        for future in concurrent.futures.as_completed(future_to_item):
                            item = future_to_item[future]
                            try:
                                result = future.result()
                                if result:
                                    results.append(result)
                            except Exception as e:
                                self.logger.error(
                                    f"处理物理状态组合 '{item['物理状态组']}-{item['物理状态']}' 时出错: {e}")
                            finally:
                                pbar.update(1)
                else:
                    # 串行处理
                    for item in identified_states:
                        try:
                            result = process_item(item)
                            if result:
                                results.append(result)
                        except Exception as e:
                            self.logger.error(f"处理物理状态组合 '{item['物理状态组']}-{item['物理状态']}' 时出错: {e}")
                        finally:
                            pbar.update(1)

        return results

    def _process_single_batch(self, text, group, states):
        """
        处理单个批次的状态组合，简化提示和错误处理

        参数:
            text: 文档文本内容
            group: 物理状态组名称
            states: 该组下的物理状态列表

        返回:
            提取结果列表
        """
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
试验项目通常包括以下关键词：
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

请重点关注与此相关的描述。

【风险评价判断标准】
风险评价判断时，请遵循以下规则：
- "可用"通常对应描述："常规结构"、"无可靠性隐患"、"满足宇航应用要求"
- "限用"通常对应描述："存在风险"、"建议评估后使用"、"限制条件使用"
- "禁用"通常对应描述："不适合宇航应用"、"严重隐患"、"不满足标准要求"

【物理状态值提取指南】
请基于文档内容提取物理状态值，注意以下标准化规则：
- 当描述类似于常见行业表达时，应提取为对应的标准物理状态值
- 尽量提取具体数值或明确表述，避免模糊表达

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
            text_front = text[:max_text_length // 2]
            text_back = text[-max_text_length // 2:]
            truncated_text = f"{text_front}\n\n[... 中间文本省略 ...]\n\n{text_back}"
            prompt += truncated_text
        else:
            prompt += text

        # 调用LLM API（带重试机制）
        result = self.llm_service.call_llm(prompt)

        if not result:
            self.logger.warning(f"API返回空响应，跳过物理状态组 '{group}'")
            return []

        batch_results = []

        # 尝试直接解析为JSON数组
        json_str = self.llm_service.extract_json_from_response(result, is_array=True)
        if not json_str:
            self.logger.warning(f"无法从批处理响应中提取JSON数组，尝试查找单个JSON对象")
            # 尝试查找单个JSON对象
            json_str = self.llm_service.extract_json_from_response(result)
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

                            # 把单个项目包装成数组
                            batch_results = [single_item]
                        else:
                            self.logger.warning("提取的JSON对象缺少'物理状态组'字段")
                    else:
                        self.logger.warning("提取的JSON不是有效的对象")
                except Exception as e:
                    self.logger.error(f"解析单个JSON对象失败: {e}")
        else:
            # 成功提取到JSON数组
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

        # 检查是否成功提取
        if not batch_results:
            self.logger.warning(f"未能从物理状态组 '{group}' 提取到有效结果")
        else:
            self.logger.info(f"从物理状态组 '{group}' 提取到 {len(batch_results)} 个结果")

            # 检查结果是否完整
            expected_states = {state['物理状态'] for state in states}
            extracted_states = {item['物理状态'] for item in batch_results if '物理状态' in item}
            missing_states = expected_states - extracted_states

            if missing_states:
                self.logger.warning(f"物理状态组 '{group}' 中有未提取到的状态: {missing_states}")

                # 为缺失的状态创建默认项
                for missing in missing_states:
                    default_item = {
                        "物理状态组": group,
                        "物理状态": missing,
                        "试验项目": "文中未提及",
                        "物理状态值": "文中未提及",
                        "风险评价": "可用",  # 默认风险评价
                        "测试评语": "文档中未包含此信息"
                    }
                    batch_results.append(default_item)

        return batch_results