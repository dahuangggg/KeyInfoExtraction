import os
import sys
from pathlib import Path

# 获取项目根目录路径
ROOT_DIR = Path(__file__).parent.parent

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(ROOT_DIR)) 