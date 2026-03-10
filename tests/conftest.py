# tests/conftest.py
"""pytest 配置"""

import pytest
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
