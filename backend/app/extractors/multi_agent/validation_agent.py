import json
import logging
import re
from collections import defaultdict

from ..llm_service import LLMService
from .prompts import VALIDATION_PROMPT


class ValidationAgent:
    """
    验证Agent - 负责验证和优化提取结果，特别是拆分复杂的物理状态值

    该Agent专注于:
    1. 检查提取结果是否准确对应原始文本
    2. 识别并拆分组合在一起的多个物理状态
    3. 对每个拆分后的物理状态赋予适当的值
    4. 确保测试评语和禁限用信息的一致性
    """

    def __init__(self, llm_service, debug=False):
        """
        初始化验证Agent

        参数:
            llm_service: LLMService实例，用于调用大语言模型
            debug: 是否启用调试模式
        """
        self.llm_service = llm_service
        self.debug = debug

        # 配置日志
        self.logger = logging.getLogger("ValidationAgent")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)

        self.logger.info("初始化ValidationAgent...")
        self.logger.info("ValidationAgent初始化完成。")

    def validate_extraction_results(self, text, extraction_results):
        """
        验证提取结果并优化，尤其是拆分复杂的物理状态值

        参数:
            text: 原始文本内容
            extraction_results: 初步提取的结果

        返回:
            优化后的提取结果
        """
        self.logger.info(f"开始验证和优化{len(extraction_results)}个提取结果...")

        # 按物理状态组组织结果，方便后续处理
        organized_results = self._organize_results_by_group(extraction_results)

        # 逐个验证各物理状态组的结果
        validated_results = []
        for group_name, group_results in organized_results.items():
            # 对每个组单独进行验证
            validated_group_results = self._validate_group_results(text, group_name, group_results)
            # 将验证后的结果添加到总结果列表
            validated_results.extend(validated_group_results)

        self.logger.info(f"验证和优化完成，最终结果包含{len(validated_results)}个项目")
        return validated_results

    def _organize_results_by_group(self, extraction_results):
        """将提取结果按物理状态组组织"""
        organized = defaultdict(list)
        for result in extraction_results:
            group = result.get("物理状态组", "未知组")
            organized[group].append(result)
        return organized

    def _validate_group_results(self, text, group_name, group_results):
        """验证特定物理状态组的结果"""
        self.logger.info(f"验证物理状态组 '{group_name}' 的{len(group_results)}个结果...")

        # 构建验证提示
        prompt = self._build_validation_prompt(text, group_name, group_results)

        # 调用LLM进行验证
        validation_response = self.llm_service.call_llm(prompt)

        if not validation_response:
            self.logger.warning(f"验证物理状态组 '{group_name}' 时获取空响应，将使用原始结果")
            return group_results

        # 从响应中提取JSON
        validated_json = self.llm_service.extract_json_from_response(validation_response, is_array=True)

        if not validated_json:
            self.logger.warning(f"无法从验证响应中提取JSON，将使用原始结果")
            return group_results

        # 解析验证结果
        try:
            validated_results = json.loads(validated_json)

            # 验证结果合法性
            if not isinstance(validated_results, list):
                self.logger.warning(f"验证结果不是列表类型，将使用原始结果")
                return group_results

            # 确保结果具有正确的物理状态组
            for result in validated_results:
                if not isinstance(result, dict):
                    continue

                # 确保包含物理状态组字段
                if "物理状态组" not in result:
                    result["物理状态组"] = group_name
                # 修正可能的物理状态组不一致
                elif result["物理状态组"] != group_name:
                    result["物理状态组"] = group_name

            # 检查结果数量是否增加（表示已成功拆分）
            if len(validated_results) > len(group_results):
                self.logger.info(
                    f"成功拆分物理状态组 '{group_name}' 的结果: {len(group_results)} -> {len(validated_results)}")
            else:
                self.logger.info(f"验证物理状态组 '{group_name}' 完成，未发现需要拆分的结果")

            return validated_results

        except json.JSONDecodeError as e:
            self.logger.error(f"解析验证JSON结果失败: {e}")
            self.logger.debug(f"验证JSON内容: {validated_json}")
            return group_results
        except Exception as e:
            self.logger.error(f"验证处理过程出错: {e}")
            return group_results

    def _build_validation_prompt(self, text, group_name, group_results):
        """构建验证提示"""
        # 转换提取结果为JSON字符串，便于在提示中使用
        results_json = json.dumps(group_results, ensure_ascii=False, indent=2)

        # 使用模板构建完整提示
        return VALIDATION_PROMPT.format(
            original_text=text,
            group_name=group_name,
            extraction_results=results_json
        )

    def validate_single_result(self, text, extraction_result):
        """
        验证单个提取结果

        参数:
            text: 原始文本内容
            extraction_result: 单个提取结果

        返回:
            验证后的结果列表（可能是拆分后的多个结果）
        """
        group_name = extraction_result.get("物理状态组", "未知组")

        # 将单个结果放入列表中，与一般验证流程保持一致
        group_results = [extraction_result]

        # 使用组验证逻辑处理单个结果
        return self._validate_group_results(text, group_name, group_results)