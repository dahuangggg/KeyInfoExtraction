import json
import logging
import re
from ..llm_service import LLMService
from .prompts import IDENTIFICATION_PROMPT


class IdentificationAgent:
    """
    识别Agent - 负责从文档中识别各种物理状态组和物理状态

    该Agent专注于:
    1. 识别文档中的物理状态组和物理状态
    2. 分析文档结构以提取隐含的物理状态信息
    3. 支持完整识别和简化识别两种模式
    4. 向CoordinatorAgent提供识别结果，以便进一步提取具体值
    """

    def __init__(self, llm_service, debug=False):
        """
        初始化识别Agent

        参数:
            llm_service: LLMService实例，用于调用大语言模型
            debug: 是否启用调试模式
        """
        self.llm_service = llm_service
        self.debug = debug

        # 配置日志
        self.logger = logging.getLogger("IdentificationAgent")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if not debug else logging.DEBUG)

        self.logger.info("初始化IdentificationAgent...")
        self.logger.info("IdentificationAgent初始化完成。")

    def identify_groups_and_states(self, text):
        """
        识别文档中出现的物理状态组和物理状态

        参数:
            text: 待分析的文档文本
            use_simplified_prompt: 是否使用简化的提示（用于备用提取）

        返回:
            识别出的物理状态组和物理状态列表
        """
        self.logger.info("正在识别文档中的物理状态组和物理状态...")

        # 提示模板
        prompt = IDENTIFICATION_PROMPT + text

        # 限制文本长度，避免超出模型的处理能力
        max_text_length = 20000  # 根据模型能力调整，避免超过模型的token限制
        if len(prompt) > max_text_length:
            raise ValueError(f"文本长度超出限制: 最大允许长度为{max_text_length}字符")

        if self.debug:
            self.logger.debug(f"使用的提示模板: {prompt[:200]}...")

        # 调用LLM API
        result = self.llm_service.call_llm(prompt)

        if self.debug:
            self.logger.debug(f"API响应: {result[:500]}...")

        # 解析结果
        try:
            # 从结果中提取JSON部分
            json_str = self.llm_service.extract_json_from_response(result)
            if not json_str:
                self.logger.error("无法从响应中提取JSON")
                return []

            # 清理JSON字符串
            json_str = json_str.strip()
            if not json_str.startswith('{'):
                self.logger.error(f"JSON字符串格式不正确: {json_str[:100]}")
                return []

            data = json.loads(json_str)

            # 处理可能出现的大小写问题
            if "identified_States" in data and "identified_states" not in data:
                data["identified_states"] = data.pop("identified_States")
                self.logger.debug("已将'identified_States'(大写S)转换为'identified_states'(小写s)")

            identified_states = data.get("identified_states", [])
            
            if not isinstance(identified_states, list):
                self.logger.error(f"identified_states不是列表类型: {type(identified_states)}")
                return []

            self.logger.info(f"识别出{len(identified_states)}个物理状态组合")
            for item in identified_states:
                if not isinstance(item, dict):
                    self.logger.error(f"物理状态项不是字典类型: {type(item)}")
                    continue
                if '物理状态组' not in item or '物理状态' not in item:
                    self.logger.error(f"物理状态项缺少必要字段: {item}")
                    continue
                self.logger.debug(f"  - {item['物理状态组']} -> {item['物理状态']}")

            return identified_states
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            self.logger.debug(f"原始JSON字符串: {json_str}")
            return []
        except Exception as e:
            self.logger.error(f"解析识别结果失败: {e}")
            self.logger.debug(f"原始结果: {result}")
            return []