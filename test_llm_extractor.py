import os
import json
from extractors.llm_extractor import LLMExtractor

def test_extraction(api_key, model_name="gpt-3.5-turbo", section_type="标识部分"):
    """
    测试LLM提取器的效果
    
    参数:
        api_key: OpenAI API密钥
        model_name: 模型名称，默认为gpt-3.5-turbo
        section_type: 要提取的章节类型
    """
    # 示例文本
    sample_text = """
    标识部分：
    器件型号规格为9288RH，生产批次为1440，生产厂标识为B。
    标识采用油墨印刷方式，标识牢固度良好。
    存在的问题：缺少静电敏感度标识信息，建议在管壳正面增加管脚定位标识。
    """
    
    # 初始化提取器
    extractor = LLMExtractor(
        model_name=model_name,
        use_api=True,
        api_key=api_key,
        temperature=0.1,
        max_tokens=2000
    )
    
    # 提取信息
    print(f"使用模型 {model_name} 提取 {section_type} 信息...")
    result = extractor.extract_info(sample_text, section_type)
    
    # 打印结果
    print("\n提取结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 评分
    score_info = extractor.score_extraction_result(result, sample_text)
    print("\n评分结果:")
    print(json.dumps(score_info, ensure_ascii=False, indent=2))
    
    return result

def test_ensemble_extraction(api_key, section_type="标识部分"):
    """
    测试多模型集成提取效果
    
    参数:
        api_key: OpenAI API密钥
        section_type: 要提取的章节类型
    """
    # 示例文本
    sample_text = """
    封装结构：
    器件采用CQFP48陶瓷封装，封装材料包括Au/Sn合金、Fe/Ni合金和CuAg焊料。
    封装工艺为焊料环熔封密封工艺，质量评估为良好。
    """
    
    # 初始化提取器
    extractor = LLMExtractor(
        model_name="gpt-3.5-turbo",
        use_api=True,
        api_key=api_key
    )
    
    # 定义多个模型
    models = ["gpt-3.5-turbo", "gpt-4"]
    
    # 提取信息
    print(f"使用模型集成 {', '.join(models)} 提取 {section_type} 信息...")
    result = extractor.extract_info_ensemble(sample_text, section_type, models=models)
    
    # 打印结果
    print("\n集成提取结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result

def test_async_extraction(api_key, model_name="gpt-3.5-turbo", section_type="芯片"):
    """
    测试异步提取效果
    
    参数:
        api_key: OpenAI API密钥
        model_name: 模型名称，默认为gpt-3.5-turbo
        section_type: 要提取的章节类型
    """
    import asyncio
    
    # 示例文本
    sample_text = """
    芯片：
    芯片装配结构为单芯片结构，芯片粘接材料为银胶。
    芯片安装工艺采用自动化贴片工艺，芯片结构和工艺为CMOS工艺。
    """
    
    # 初始化提取器
    extractor = LLMExtractor(
        model_name=model_name,
        use_api=True,
        api_key=api_key
    )
    
    # 异步提取信息
    print(f"异步使用模型 {model_name} 提取 {section_type} 信息...")
    result = asyncio.run(extractor.extract_info_async(sample_text, section_type))
    
    # 打印结果
    print("\n异步提取结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result

if __name__ == "__main__":
    # 从环境变量或用户输入获取API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = input("请输入您的OpenAI API密钥: ")
    
    # 测试基本提取
    test_extraction(api_key, model_name="gpt-3.5-turbo", section_type="标识部分")
    
    # 是否继续测试
    continue_test = input("\n是否继续测试多模型集成提取? (y/n): ")
    if continue_test.lower() == 'y':
        test_ensemble_extraction(api_key, section_type="封装结构")
    
    continue_test = input("\n是否继续测试异步提取? (y/n): ")
    if continue_test.lower() == 'y':
        test_async_extraction(api_key, model_name="gpt-3.5-turbo", section_type="芯片") 