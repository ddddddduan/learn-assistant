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

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        log.FileHandler("../log/brush_video.log"),
        log.StreamHandler()
    ]
)

# 从配置文件读取参数
base_url, access_token, db_path = read_config.video_config()


class BrushVideo:
    # 常量定义
    COURSE_BTN_SELECTOR = 'a.btn.course-btn'
    SUBJECT_NAME_SELECTOR = 'div.course-name'
    VIDEO_CONTAINER_ID = 'vjs_video_3_html5_api'
    MAX_RETRIES = 3

    def __init__(self):
        self.base_url = base_url
        self.db_path = db_path
        self.course_list = []
        self.driver = self._init_browser()
        self._set_cookies()
        self._init_db()

    def _init_browser(self):
        """初始化浏览器驱动"""
        options = webdriver.EdgeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless=new")
        options.add_argument("--mute-audio")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        try:
            # 优先使用新版本API
            service = Service(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)
        except WebDriverException as e:
            log.error(f"浏览器初始化失败: {e}")
            raise

    def _set_cookies(self):
        """动态设置Cookie"""
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # 动态解析域名
            domain = self.base_url.split('//')[-1].split('/')[0]

            cookies = [
                {
                    'name': '__environment',
                    'value': 'production',
                    'domain': domain,
                    'path': '/',
                    'secure': True,
                    'httpOnly': False
                },
                {
                    'name': 'AccessToken',
                    'value': access_token,
                    'domain': domain,
                    'path': '/',
                    'secure': True,
                    'httpOnly': True
                }
            ]

            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.driver.refresh()
            self._wait_for_element(By.TAG_NAME, "body")
        except Exception as e:
            log.error(f"Cookie设置失败: {e}")
            raise

    def _init_db(self):
        """数据库初始化"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learn_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    semester INTEGER NOT NULL,
                    processed INTEGER DEFAULT 0,
                    UNIQUE(subject, course_id)
                )
            ''')
            conn.commit()

    def run(self, start_subject=None):
        """主运行逻辑"""
        subjects = self._get_subject_list()
        log.info(f"科目列表获取成功:{subjects}")
        current_subject = self._get_start_subject(subjects, start_subject)
        subject_index = self._get_subject_index(subjects, current_subject)

        while current_subject:
            log.info(f"正在处理科目: {current_subject}")
            try:
                self._process_subject(current_subject, subject_index)
                current_subject = self._get_next_subject(subjects, current_subject)
            except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
                log.warning(f"遇到页面异常: {e}")
                if not self._handle_retry(current_subject, subject_index):
                    log.error("超过最大重试次数，终止运行")
                    break
            except Exception as e:
                log.error(f"未知错误: {e}")
                break

        self.driver.quit()
        log.info("刷课任务完成")

    def _process_subject(self, subject, subject_index):
        """处理单个科目"""
        self._navigate_to_subject(subject, subject_index)
        self._load_course_list(subject)

        # 从db恢复
        start_id = self._get_last_processed_course_id(subject) or self.course_list[0]
        log.info(f"从课程 {start_id} 开始处理")
        start_index = self.course_list.index(start_id) if start_id in self.course_list else 0

        for idx, course_id in enumerate(self.course_list[start_index:], start_index):
            retry_count = 0
            while retry_count < self.MAX_RETRIES:
                try:
                    self._process_course(course_id, subject)
                    break
                except Exception as e:
                    retry_count += 1
                    log.warning(f"课程 {course_id} 第{retry_count}次重试，错误: {e}")
                    self._reload_subject_page(subject, subject_index)

    def _process_course(self, course_id, subject):
        """处理单个课程"""
        log.info(f"开始处理课程: {course_id}")
        self._click_element(By.ID, course_id)
        video = self._wait_for_video()
        # 强制开始播放
        self.driver.execute_script("arguments[0].play();", video)
        log.info("已发送播放指令")

        duration = self._get_video_duration(video)
        log.info(f"视频时长: {self._format_time(duration)}")

        self._wait_video_complete(video, duration)
        self._mark_course_complete(subject, course_id)
        self._return_to_course_list()

    # ------------------- 核心功能方法 -------------------
    def _get_subject_list(self):
        """获取科目列表"""
        self.driver.get(self.base_url)
        elements = self._wait_for_elements(By.CSS_SELECTOR, self.SUBJECT_NAME_SELECTOR)
        return [el.text.strip() for el in elements]

    def _get_subject_index(self, subjects, tartget_subject):
        for i, subject in enumerate(subjects):
            log.info(f'科目：{subject}，科目索引：{i}')
            if subject == tartget_subject:
                return i
        return 0

    def _navigate_to_subject(self, subject, subject_index):
        """导航到指定科目"""
        btn = self._find_subject_button(subject, subject_index)
        btn.click()
        self._wait_for_element(By.XPATH, "//span[text()='课程讲授']").click()
        self._wait_for_element(By.CSS_SELECTOR, "ul.level-root")

    def _load_course_list(self, subject):
        """加载课程列表到内存"""
        uls = self._wait_for_elements(By.CSS_SELECTOR, "ul.level-root")
        self.course_list = [
            el.get_attribute('id')
            for ul in uls
            for el in ul.find_elements(By.XPATH, ".//a[contains(@id, 'courseware-kcjs_')]")
        ]
        self._save_course_list_to_db(subject)
        log.info(f"加载到{len(self.course_list)}个课程")

    def _wait_video_complete(self, video_element, max_duration):
        """智能等待视频播放完成（增强版）"""
        try:
            # 阶段1：等待开始播放
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script("return arguments[0].currentTime > 0", video_element)
            )

            # 阶段2：跟踪播放进度
            start_time = time.time()
            last_progress = 0

            while True:
                current_time = self.driver.execute_script("return arguments[0].currentTime", video_element)
                progress = (current_time / max_duration) * 100

                # 进度跟踪
                if progress - last_progress > 10:
                    log.info(f"播放进度: {progress:.1f}%")
                    last_progress = progress

                # 超时判断
                if time.time() - start_time > max_duration * 1.5:
                    raise TimeoutException(f"播放超时，当前进度: {current_time}s")

                # 完成判断
                if current_time >= max_duration - 1:
                    break

                time.sleep(5)

        except Exception as e:
            log.error(f"播放异常: {str(e)}")
            raise

    # ------------------- 辅助工具方法 -------------------
    def _get_start_subject(self, subjects, start_subject):
        """确定起始科目"""
        log.info(f"起始科目:{start_subject}")
        if start_subject:
            if start_subject in subjects:
                return start_subject
            log.warning(f"未找到指定科目 {start_subject}，从第一个科目开始")
        return subjects[0] if subjects else None

    def _get_next_subject(self, subjects, current_subject):
        """获取下一个科目"""
        try:
            idx = subjects.index(current_subject)
            return subjects[idx + 1] if idx + 1 < len(subjects) else None
        except ValueError:
            return None

    def _find_subject_button(self, subject, subject_index):
        """查找科目对应按钮"""
        log.info(f"当前科目：{subject},科目索引：{subject_index}")
        buttons = self._wait_for_elements(By.CSS_SELECTOR, self.COURSE_BTN_SELECTOR)
        btn = buttons[subject_index]
        if subject_index >= len(buttons):
            raise NoSuchElementException(f"未找到科目按钮: {subject}")
        else:
            return btn

    def _return_to_course_list(self):
        """返回课程列表页"""
        self._click_element(By.CSS_SELECTOR, 'span.glyphicon.glyphicon-menu-left')
        self._wait_for_element(By.XPATH, "//span[text()='课程讲授']").click()

    def _reload_subject_page(self, subject, subject_index):
        """重新加载科目页面"""
        self.driver.get(self.base_url)
        self._set_cookies()
        self._navigate_to_subject(subject, subject_index)

    # ------------------- 数据库操作 -------------------
    def _save_course_list_to_db(self, subject):
        """保存课程列表到数据库"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executemany(
                'INSERT OR IGNORE INTO learn_record (subject, course_id, semester) VALUES (?, ?, ?)',
                [(subject, cid, 3) for cid in self.course_list]
            )
            conn.commit()

    def _mark_course_complete(self, subject, course_id):
        """标记课程完成"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                'UPDATE learn_record SET processed = 1 WHERE subject = ? AND course_id = ?',
                (subject, course_id)
            )
            conn.commit()

    def _get_last_processed_course_id(self, subject):
        """获取最后处理过的课程ID"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT course_id FROM learn_record WHERE subject = ? AND processed = 0 ORDER BY id LIMIT 1',
                (subject,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    # ------------------- 元素等待方法 -------------------
    def _wait_for_element(self, by, value, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def _wait_for_elements(self, by, value, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_all_elements_located((by, value))
        )

    def _wait_for_video(self):
        """等待视频元素加载"""
        return self._wait_for_element(By.ID, self.VIDEO_CONTAINER_ID)

    def _click_element(self, by, value):
        element = self._wait_for_element(by, value)
        element.click()
        return element

    # ------------------- 其他工具方法 -------------------
    def _get_video_duration(self, video_element):
        """安全获取视频时长（增加重试机制）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 显式等待视频元数据加载
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script(
                        "return arguments[0].readyState > 0 && arguments[0].duration > 0",
                        video_element
                    )
                )
                duration = self.driver.execute_script(
                    "return arguments[0].duration || 0",
                    video_element
                )
                if duration > 0:
                    return duration
                log.warning(f"第{attempt + 1}次获取时长失败，获得{duration}秒")
                time.sleep(2)
            except StaleElementReferenceException:
                log.warning("视频元素失效，重新获取中...")
                video_element = self._wait_for_video()
        raise TimeoutError("无法获取有效视频时长")

    def _format_time(self, seconds):
        return time.strftime("%H:%M:%S", time.gmtime(seconds))

    def _handle_retry(self, current_subject, subject_index):
        """处理重试逻辑"""
        log.info("尝试恢复页面状态...")
        self._reload_subject_page(current_subject, subject_index)
        return True  # 实际可添加重试次数统计


if __name__ == '__main__':
    try:
        BrushVideo().run(start_subject='数据库原理(专升本)')
    except KeyboardInterrupt:
        log.info("用户手动中断执行")
    except Exception as e:
        log.error(f"程序异常终止: {e}")
        exit(1)
