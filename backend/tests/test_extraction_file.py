import argparse
import json
import requests
from pathlib import Path
import os
import sys
from docx import Document

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# 或者直接添加backend目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 可以导入app模块中的内容
from app.core.config import settings

# LLM API配置 - 如果settings中没有配置，则使用默认值
SERVER_IP = settings.LLM_SERVER_IP if hasattr(settings, 'LLM_SERVER_IP') else '10.112.11.125'
SERVER_PORT = settings.LLM_SERVER_PORT if hasattr(settings, 'LLM_SERVER_PORT') else '11434'
MODEL_NAME = settings.LLM_MODEL if hasattr(settings, 'LLM_MODEL') else 'deepseek-r1:32b'

def extract_from_file(file_path):
    """从文件中提取信息"""
    # 读取docx文件内容
    doc = Document(file_path)
    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    
    # 构建提示
    prompt = f"""
你是一个专业的航天电子元件物理状态分析助手。请从以下文档中提取关键的元器件物理状态信息。
首先识别所有物理状态组和其中包含的物理状态项，然后对每个物理状态项提取其典型值、禁限用信息和测试评语等信息。
请按JSON格式返回提取结果。

文档内容：
{text}

JSON格式示例：
```json
{{
  "物理状态组1": {{
    "物理状态1": {{
      "值": "具体描述",
      "禁限用信息": "如果有禁限用信息",
      "测试评语": "如果有测试评语"
    }},
    "物理状态2": {{
      "值": "具体描述",
      "禁限用信息": "如果有禁限用信息",
      "测试评语": "如果有测试评语"
    }}
  }},
  "物理状态组2": {{
    ...其他物理状态
  }}
}}
```

请确保仅返回符合上述格式的JSON数据，不要添加任何其他评论或解释。如果某个字段无内容，使用空字符串。
"""

    # 发送请求到LLM API
    print("正在发送请求到LLM API...")
    url = f"http://{SERVER_IP}:{SERVER_PORT}/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"API请求失败: {response.status_code}")
        print(response.text)
        return None
    
    # 解析结果
    try:
        result = response.json()
        content = result.get("message", {}).get("content", "")
        
        # 提取JSON
        start_idx = content.find("```json\n")
        end_idx = content.find("```", start_idx + 8)
        
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx + 8:end_idx].strip()
            extracted_data = json.loads(json_str)
        else:
            # 尝试直接解析
            extracted_data = json.loads(content)
        
        # 保存结果到文件
        output_file = Path(file_path).with_suffix('.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
        print(f"分析结果已保存到: {output_file}")
        return extracted_data
    
    except Exception as e:
        print(f"解析响应时出错: {e}")
        print(f"原始响应: {response.text}")
        return None

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从文件中提取信息")
    parser.add_argument("file", help="要处理的文件路径")
    args = parser.parse_args()
    
    # 提取信息
    extract_from_file(args.file)

if __name__ == "__main__":
    main() 