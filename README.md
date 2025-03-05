# 刷视频脚本说明

## 简介
`brush-video.py` 是一个用于自动刷视频的脚本，借助 Selenium 库实现自动化操作浏览器，同时使用 SQLite 数据库来管理课程信息。脚本从配置文件读取参数，能自动处理科目和课程，等待视频播放完成并标记课程已完成。

## 功能概述
1. **浏览器自动化**：运用 Selenium 库自动化操作 Edge 浏览器。
2. **配置管理**：从配置文件读取基础 URL、访问令牌和数据库路径。
3. **数据库管理**：使用 SQLite 数据库存储课程列表，标记课程完成状态。
4. **视频处理**：自动播放视频并等待视频播放完成。
5. **错误处理**：处理各类异常，如超时异常、元素未找到异常等。

## 代码结构
### 导入模块
```python
import logging as log
import sqlite3
import time
from contextlib import closing

from selenium import webdriver
from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
                                        WebDriverException, StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

import read_config
```

### 日志配置
```python
log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        log.FileHandler("brush_video.log"),
        log.StreamHandler()
    ]
)
```

### 配置读取
```python
base_url, access_token, db_path = read_config.video_config()
```

### `BrushVideo` 类
该类涵盖了刷视频的核心功能，包含以下方法：
1. **初始化方法**
    - `__init__`：类的构造函数。
    - `_init_browser`：初始化浏览器驱动。
    - `_set_cookies`：动态设置 Cookie。
    - `_init_db`：数据库初始化。
2. **主运行逻辑**
    - `run`：主运行逻辑，可指定起始科目。
3. **科目和课程处理**
    - `_process_subject`：处理单个科目。
    - `_process_course`：处理单个课程。
4. **核心功能方法**
    - `_get_subject_list`：获取科目列表。
    - `_get_subject_index`：获取指定科目的索引。
    - `_navigate_to_subject`：导航到指定科目。
    - `_load_course_list`：加载课程列表到内存。
    - `_wait_video_complete`：智能等待视频播放完成。
5. **辅助工具方法**
    - `_get_start_subject`：确定起始科目。
    - `_get_next_subject`：获取下一个科目。
    - `_find_subject_button`：查找科目对应按钮。
    - `_return_to_course_list`：返回课程列表页。
    - `_reload_subject_page`：重新加载科目页面。
6. **数据库操作**
    - `_save_course_list_to_db`：保存课程列表到数据库。
    - `_mark_course_complete`：标记课程完成。
    - `_get_last_processed_course_id`：获取最后处理过的课程 ID。
7. **元素等待方法**
    - `_wait_for_element`：等待单个元素加载。
    - `_wait_for_elements`：等待多个元素加载。
    - `_wait_for_video`：等待视频元素加载。
    - `_click_element`：点击指定元素。
8. **其他工具方法**
    - `_get_video_duration`：安全获取视频时长。
    - `_format_time`：格式化时间。
    - `_handle_retry`：处理重试逻辑。

### 主程序入口
```python
if __name__ == '__main__':
    try:
        BrushVideo().run(start_subject='数据库原理(专升本)')
    except KeyboardInterrupt:
        log.info("用户手动中断执行")
    except Exception as e:
        log.error(f"程序异常终止: {e}")
        exit(1)
```

## 使用方法
1. 确保已安装所需的 Python 库，可使用以下命令安装：
```bash
pip install selenium webdriver_manager
```
2. 配置 `config.json` 文件，确保能正确读取基础 URL、访问令牌和数据库路径。
3. 运行脚本：
```bash
python brush-video.py
```
4. 若要指定起始科目，可修改 `BrushVideo().run(start_subject='科目名称')` 中的 `start_subject` 参数。

## 注意事项
- 确保 Edge 浏览器已安装，并且版本与 `EdgeChromiumDriverManager` 兼容。
- 运行脚本时，可能需要处理浏览器的弹出窗口和权限请求。
- 脚本运行过程中，会将日志信息记录到 `../log/brush_video.log` 文件中，便于排查问题。

## 免责声明
本脚本仅用于技术学习和研究目的，不得用于任何违反相关网站使用条款、法律法规或道德规范的活动。使用本脚本可能会违反某些网站的反自动化机制，从而导致账号被封禁、限制使用等风险，使用者需自行承担由此带来的一切后果。作者不对因使用本脚本而造成的任何损失或损害承担责任。在使用本脚本前，请确保你已经获得了相关网站的合法授权。 
