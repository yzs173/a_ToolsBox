import os
import re
import subprocess
import requests
from lxml import html
import traceback
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QGroupBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QProgressBar, QRadioButton, 
    QButtonGroup, QTextEdit, QCheckBox, QComboBox, QSpinBox
)
import sys

TOOL_NAME = "B站视频下载器"
DESCRIPTION = "下载B站视频（需要配置环境）"

def clean_bilibili_url(url):
    if not url:
        return ""
    url = url.strip()
    url = url.split('?')[0]
    url = url.rstrip('/')
    url = url.split('@')[0]
    return url


class FetchInfoThread(QThread):
    finished_signal = pyqtSignal(bool, dict, str)
    log_signal = pyqtSignal(str)

    def __init__(self, url, cookies_path=None):
        super().__init__()
        self.url = clean_bilibili_url(url)
        self.cookies_path = cookies_path

    def run(self):
        try:
            self.log_signal.emit(f"[信息] 清洗后 URL: {self.url}")
            self.log_signal.emit("[信息] 使用 you-get -i 获取视频信息...")
            
            cmd = ["you-get", "-i"]
            
            if self.cookies_path and os.path.exists(self.cookies_path):
                cmd.extend(["-c", self.cookies_path])
                self.log_signal.emit(f"[配置] 使用 cookies: {self.cookies_path}")
            
            cmd.append(self.url)
            
            self.log_signal.emit(f"[调试] 执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            self.log_signal.emit(f"[调试] you-get -i 原始输出:\n{'-'*50}\n{result.stdout}\n{'-'*50}")
            
            if result.returncode != 0:
                err_msg = result.stderr or result.stdout
                self.log_signal.emit(f"[错误] {err_msg[:300]}")
                self.finished_signal.emit(False, {}, f"获取视频信息失败: {err_msg[:200]}")
                return
            
            formats = self._parse_formats_from_text(result.stdout)
            title = self._parse_title(result.stdout)
            permission_info = self._analyze_permission(formats, result.stdout)
            
            self.finished_signal.emit(
                True, 
                {"formats": formats, "title": title, "permission": permission_info}, 
                "获取成功"
            )
            
        except subprocess.TimeoutExpired:
            self.log_signal.emit("[错误] 获取视频信息超时（30秒）")
            self.finished_signal.emit(False, {}, "获取视频信息超时")
        except Exception as e:
            self.log_signal.emit(f"[异常] {str(e)}")
            self.finished_signal.emit(False, {}, f"获取视频信息出错: {str(e)}")

    def _parse_title(self, text):
        for line in text.split('\n'):
            if line.strip().startswith("title:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _parse_formats_from_text(self, text):
        formats = []
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            fmt_match = re.match(r'-\s+format:\s+(\S+)', line)
            if fmt_match:
                raw_format = fmt_match.group(1)
                clean_format = raw_format.split('?')[0].split('/')[0]
                
                if not re.search(r'(flv|mp4|hevc|avc|av1|dash)', clean_format, re.IGNORECASE):
                    self.log_signal.emit(f"[调试] 忽略非视频format: {clean_format}")
                    i += 1
                    continue
                
                fmt = {"format": clean_format}
                self.log_signal.emit(f"[调试] 匹配到有效format: {clean_format}")
                
                for j in range(i + 1, min(i + 6, len(lines))):
                    qm = re.match(r'\s+quality:\s*(.+)', lines[j])
                    if qm:
                        fmt["quality"] = qm.group(1).strip()
                    
                    sm = re.match(r'\s+size:\s*([\d.]+\s*\w+)', lines[j])
                    if sm:
                        fmt["size"] = sm.group(1)
                    
                    cm = re.match(r'\s+container:\s*(\S+)', lines[j])
                    if cm:
                        fmt["container"] = cm.group(1)
                
                if "quality" not in fmt:
                    fmt["quality"] = clean_format
                
                if clean_format not in [f["format"] for f in formats]:
                    formats.append(fmt)
            
            i += 1
        
        if not formats:
            self.log_signal.emit("[调试] 未找到任何符合规则的format条目")
        else:
            self.log_signal.emit(f"[调试] 解析完成，共找到 {len(formats)} 个清晰度")
        
        def sort_key(f):
            q = f.get("quality", "").lower()
            if "4k" in q or "2160" in q:
                return 4
            elif "1080" in q:
                return 3
            elif "720" in q:
                return 2
            elif "480" in q:
                return 1
            else:
                return 0
        
        formats.sort(key=sort_key, reverse=True)
        return formats

    def _analyze_permission(self, formats, raw_output):
        result = {
            "has_4k": False,
            "has_1080p60": False,
            "has_high_quality": False,
            "is_paid_or_vip_only": False,
            "max_quality": "480P",
            "warning": ""
        }
        
        if not formats:
            return result
        
        all_qualities = " ".join([f.get("quality", "") for f in formats])
        
        if re.search(r'4K|2160P', all_qualities, re.IGNORECASE):
            result["has_4k"] = True
            result["has_high_quality"] = True
            result["max_quality"] = "4K"
        
        if re.search(r'1080P60|1080P.*60', all_qualities, re.IGNORECASE):
            result["has_1080p60"] = True
            result["has_high_quality"] = True
            if result["max_quality"] != "4K":
                result["max_quality"] = "1080P60"
        
        if re.search(r'720P60|720P.*60', all_qualities, re.IGNORECASE):
            result["has_high_quality"] = True
            if result["max_quality"] in ["480P", "720P"]:
                result["max_quality"] = "720P60"
        elif "720P" in all_qualities:
            if result["max_quality"] == "480P":
                result["max_quality"] = "720P"
        
        if any(k in raw_output for k in ["充电", "VIP", "大会员", "专享", "充电后才能观看", "仅限大会员", "试看"]):
            result["is_paid_or_vip_only"] = True
        
        if result["is_paid_or_vip_only"] and not result["has_high_quality"]:
            result["warning"] = "⚠️ 该视频为大会员/充电专享，当前账号无权下载高清晰度"
        elif result["has_4k"] and result["max_quality"] != "4K":
            result["warning"] = "⚠️ 检测到4K源，但当前账号无法获取4K清晰度"
        
        return result


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, int, int, str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url, output_dir, download_type, cookies_path=None, format_choice=None, max_workers=3):
        super().__init__()
        self.raw_url = url
        self.url = clean_bilibili_url(url)
        self.output_dir = os.path.abspath(output_dir)
        self.download_type = download_type
        self.cookies_path = cookies_path
        self.format_choice = format_choice
        self.max_workers = max_workers
        self._stop = False

    def run(self):
        try:
            if self.download_type == "collection":
                self._download_collection()
            else:
                self._download_single(self.url, 1, 1)
            self.finished_signal.emit(True, "下载完成！")
        except Exception as e:
            self.finished_signal.emit(False, f"下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_collection(self):
        urls = self._get_collection_urls()
        total = len(urls)
        self.log_signal.emit(f"[合集/分P] 共检测到 {total} 个视频，并发数: {self.max_workers}")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def worker(video_url, idx):
            if self._stop:
                return
            self._download_single(video_url, idx, total)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(worker, url, i + 1): (i + 1, url)
                for i, url in enumerate(urls)
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    idx, url = futures[future]
                    self.log_signal.emit(f"[错误] 第 {idx} 个视频失败: {url}\n{str(e)}")

    def _get_collection_urls(self):
        """获取合集中的所有视频URL"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(self.url, headers=headers, timeout=15)
        resp.raise_for_status()
        tree = html.fromstring(resp.content)
        
        # 1. 检测合集 (video-pod__list section)
        elements = tree.xpath("//*[@data-key]")
        keys = [e.get("data-key") for e in elements]
        
        if keys and keys[0].startswith("BV"):
            self.log_signal.emit(f"[合集检测] 检测到合集，共 {len(keys)} 个视频")
            return [f"https://www.bilibili.com/video/{k}" for k in keys]
        
        # 2. 单视频或分P视频
        return [self.url]

    def _download_single(self, url, current, total):
        cmd = self._build_base_cmd(url)
        self.log_signal.emit(f"[下载] 第 {current}/{total} 个视频")
        self._execute_download_command(cmd, current, total)

    def _build_base_cmd(self, url):
        """
        构建下载命令
        关键修改：
        1. 合集模式下，对所有视频使用-l参数
        2. 单视频模式下，仅对基础BV链接使用-l参数
        """
        cmd = ["you-get"]

        # 合集模式：对所有视频使用-l参数下载全部分P
        if self.download_type == "collection":
            cmd.append("-l")
        else:
            # 分P视频
            is_base_bv_link = bool(re.match(r"^https?://(www\.)?bilibili\.com/video/BV\w+$", url))
            if is_base_bv_link:
                cmd.append("-l")

        # 清晰度选择
        if self.format_choice and self.format_choice != "默认":
            cmd.append(f"--format={self.format_choice}")
            self.log_signal.emit(f"[配置] 使用清晰度: --format={self.format_choice}")

        # Cookies
        if self.cookies_path and os.path.exists(self.cookies_path):
            cmd.extend(["-c", self.cookies_path])
            self.log_signal.emit(f"[配置] 使用 cookies: {self.cookies_path}")

        # 通用参数
        cmd.extend([
            "--no-caption",
            "-o", self.output_dir,
            "--debug",
            "--", url  # URL 放在最后
        ])

        return cmd

    def _execute_download_command(self, cmd, current, total):
        self.log_signal.emit(f"执行命令: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace"
        )

        video_title = "未知视频"
        percent = 0

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                text = line.strip()
                self.log_signal.emit(text)

                if "title:" in text.lower():
                    video_title = text.split(":", 1)[-1].strip()

                m = re.search(r"(\d+\.\d+)%", text)
                if m:
                    percent = int(float(m.group(1)))
                    self.progress_signal.emit(current, total, percent, video_title)
                elif "100%" in text:
                    self.progress_signal.emit(current, total, 100, video_title)

        if process.returncode != 0:
            raise Exception(f"下载失败，退出码: {process.returncode}")


class BilibiliDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B站视频下载器")
        self.setMinimumSize(950, 900)  # 稍微减小高度，移除了信息标签
        self.output_dir = os.path.expanduser("~\Downloads")
        self.cookies_path = ""
        self.use_cookies = False
        self.available_formats = []
        self.current_video_info = {}
        self.max_workers = 3
        self.permission_info = {}
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout()

        type_group = QButtonGroup(self)
        self.single_radio = QRadioButton("单个视频")
        self.collection_radio = QRadioButton("视频合集/分P")
        type_group.addButton(self.single_radio)
        type_group.addButton(self.collection_radio)
        self.single_radio.setChecked(True)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("下载类型:"))
        type_layout.addWidget(self.single_radio)
        type_layout.addWidget(self.collection_radio)
        type_layout.addStretch()

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴 B 站视频链接（自动清洗 ?vd_source=xxx）")
        self.url_input.setStyleSheet("padding:8px; font-size:14px;")
        
        self.fetch_info_btn = QPushButton("获取清晰度")
        self.fetch_info_btn.clicked.connect(self._fetch_video_info)
        self.fetch_info_btn.setStyleSheet("padding:8px 12px; background:#FF9800; color:black;")
        
        url_layout.addWidget(QLabel("视频链接:"))
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_info_btn)

        quality_group = QGroupBox("清晰度选择（红色为无权限）")
        quality_layout = QHBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("默认（最高清晰度）", "默认")
        self.quality_combo.setMinimumWidth(450)
        self.quality_combo.setEnabled(False)
        
        self.quality_info_label = QLabel("请先获取视频清晰度")
        self.quality_info_label.setStyleSheet("color: #666; font-style: italic;")
        
        quality_layout.addWidget(QLabel("选择清晰度:"))
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addWidget(self.quality_info_label)
        quality_layout.addStretch()
        
        quality_group.setLayout(quality_layout)

        self.permission_label = QLabel("")
        self.permission_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #856404;
                padding: 8px;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.permission_label.setVisible(False)

        cookies_group = QGroupBox("Cookies设置（必须用于大会员/充电视频）")
        cookies_layout = QVBoxLayout()
        
        self.use_cookies_checkbox = QCheckBox("启用Cookies（下载4K/1080P60必须勾选）")
        self.use_cookies_checkbox.stateChanged.connect(self._toggle_cookies_controls)
        
        cookies_path_layout = QHBoxLayout()
        self.cookies_path_label = QLabel("Cookies文件:")
        self.cookies_path_input = QLineEdit()
        self.cookies_path_input.setPlaceholderText("选择 cookies.txt（从浏览器导出）")
        self.cookies_path_input.setEnabled(False)
        
        self.browse_cookies_btn = QPushButton("浏览...")
        self.browse_cookies_btn.clicked.connect(self._select_cookies_file)
        self.browse_cookies_btn.setEnabled(False)
        
        cookies_path_layout.addWidget(self.cookies_path_label)
        cookies_path_layout.addWidget(self.cookies_path_input)
        cookies_path_layout.addWidget(self.browse_cookies_btn)
        
        cookies_layout.addWidget(self.use_cookies_checkbox)
        cookies_layout.addLayout(cookies_path_layout)
        cookies_group.setLayout(cookies_layout)

        concurrent_group = QGroupBox("下载加速（仅合集生效）")
        concurrent_layout = QHBoxLayout()
        
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 5)
        self.concurrent_spin.setValue(3)
        self.concurrent_spin.setToolTip("同时下载的视频数量（B站建议 ≤5，否则可能 403）")
        
        concurrent_layout.addWidget(QLabel("并发数:"))
        concurrent_layout.addWidget(self.concurrent_spin)
        concurrent_layout.addStretch()
        
        concurrent_group.setLayout(concurrent_layout)

        self.path_label = QLabel(f"保存路径: {self.output_dir}")
        path_btn = QPushButton("更改路径", clicked=self._select_path)
        path_btn.setStyleSheet("padding:6px 12px; background:#4CAF50; color:black;")

        self.download_btn = QPushButton("开始下载", clicked=self._start_download)
        self.download_btn.setStyleSheet("padding:12px 24px; background:#2196F3; color:black; font-size:16px;")

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress.setVisible(False)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            font-family: Consolas; 
            font-size: 12px; 
            background-color: #1E1E1E; 
            color: #D4D4D4;
            padding: 10px;
        """)
        self.log_view.setMinimumHeight(250)

        layout.addLayout(type_layout)
        layout.addLayout(url_layout)
        layout.addWidget(quality_group)
        layout.addWidget(self.permission_label)
        layout.addWidget(cookies_group)
        layout.addWidget(concurrent_group)
        layout.addWidget(self.path_label)
        layout.addWidget(path_btn)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("操作日志（含you-get原始输出，用于排查问题）:"))
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def _fetch_video_info(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "输入错误", "请输入B站视频链接")
            return
        
        cleaned_url = clean_bilibili_url(url)
        self.url_input.setText(cleaned_url)
        
        if not re.match(r"^https?://(www\.)?bilibili\.com/video/BV\w+", cleaned_url):
            QMessageBox.warning(self, "输入错误", "请输入有效的B站视频链接（BV号格式）")
            return
        
        self.log_view.append(f"[信息] 原始 URL: {url[:50]}...")
        self.log_view.append(f"[信息] 清洗后 URL: {cleaned_url}")
        self.log_view.append("[信息] 正在获取视频信息...")
        
        self.fetch_info_btn.setEnabled(False)
        self.fetch_info_btn.setText("获取中...")
        self.quality_combo.clear()
        self.quality_combo.addItem("默认（最高清晰度）", "默认")
        self.quality_combo.setEnabled(False)
        self.permission_label.setVisible(False)
        
        cookies_path = self.cookies_path if self.use_cookies else None
        
        self.fetch_thread = FetchInfoThread(cleaned_url, cookies_path)
        self.fetch_thread.finished_signal.connect(self._on_fetch_info_finished)
        self.fetch_thread.log_signal.connect(self.log_view.append)
        self.fetch_thread.start()

    def _on_fetch_info_finished(self, success, info, message):
        self.fetch_info_btn.setEnabled(True)
        self.fetch_info_btn.setText("获取清晰度")
        
        if success:
            self.current_video_info = info
            self.available_formats = info.get("formats", [])
            self.permission_info = info.get("permission", {})
            
            self.quality_combo.clear()
            self.quality_combo.addItem("默认（最高清晰度）", "默认")
            
            if self.available_formats:
                for fmt in self.available_formats:
                    format_key = fmt.get("format", "")
                    quality = fmt.get("quality", "")
                    size = fmt.get("size", "")
                    container = fmt.get("container", "")
                    
                    display_text = f"{quality} [{format_key}]"
                    if size:
                        display_text += f" · {size}"
                    if container:
                        display_text += f" ({container})"
                    
                    self.quality_combo.addItem(display_text, format_key)
                
                self.quality_combo.setEnabled(True)
                title = info.get("title", "")
                title_hint = f"「{title[:30]}」" if title else ""
                
                perm = self.permission_info
                if perm.get("warning"):
                    self.permission_label.setText(perm["warning"])
                    self.permission_label.setVisible(True)
                    self.log_view.append(f"[警告] {perm['warning']}")
                
                max_q = perm.get("max_quality", "480P")
                self.quality_info_label.setText(
                    f"{title_hint} 最高: {max_q} | 共 {len(self.available_formats)} 种清晰度"
                )
                self.quality_info_label.setStyleSheet("color: #28a745;")
                self.log_view.append(f"[成功] {message}，最高清晰度: {max_q}")
            else:
                self.quality_info_label.setText("未检测到清晰度信息")
                self.quality_info_label.setStyleSheet("color: #ffc107;")
                possible_reasons = [
                    "1. 未启用Cookies或Cookies无效",
                    "2. 当前账号无该视频的观看权限",
                    "3. you-get版本过旧，建议升级：pip install -U you-get",
                    "4. 视频已被下架或设为私密"
                ]
                reason_text = "\n".join(possible_reasons)
                self.log_view.append(f"[警告] {message}，但未解析到清晰度信息。可能原因：\n{reason_text}")
        else:
            self.quality_info_label.setText("获取清晰度失败")
            self.quality_info_label.setStyleSheet("color: #dc3545;")
            self.log_view.append(f"[错误] {message}")
            QMessageBox.warning(self, "获取失败", message)

    def _toggle_cookies_controls(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.cookies_path_input.setEnabled(enabled)
        self.browse_cookies_btn.setEnabled(enabled)
        self.use_cookies = enabled
        
        if not enabled:
            self.cookies_path_input.clear()
            self.cookies_path = ""

    def _select_cookies_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Cookies文件",
            "",
            "Cookies文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            self.cookies_path = file_path
            self.cookies_path_input.setText(file_path)
            self.log_view.append(f"[配置] 已选择cookies文件: {file_path}")

    def _select_path(self):
        if path := QFileDialog.getExistingDirectory(self, "选择保存路径"):
            self.output_dir = os.path.abspath(path)
            self.path_label.setText(f"保存路径: {self.output_dir}")
            self.log_view.append(f"[配置] 保存路径已更改为: {self.output_dir}")

    def _start_download(self):
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.download_btn.setEnabled(False)
        self.log_view.clear()

        url = self.url_input.text().strip()
        cleaned_url = clean_bilibili_url(url)
        self.url_input.setText(cleaned_url)
        
        if not re.match(r"^https?://(www\.)?bilibili\.com/video/BV\w+", cleaned_url):
            QMessageBox.warning(self, "输入错误", "请输入有效的B站视频链接")
            self.download_btn.setEnabled(True)
            return

        perm = self.permission_info
        if perm.get("only_trial"):
            reply = QMessageBox.question(
                self, "确认下载",
                "检测到当前账号仅能试看该视频（约30秒）。\n确定要继续下载试看版吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.download_btn.setEnabled(True)
                return

        download_type = "collection" if self.collection_radio.isChecked() else "video"
        cookies_path = self.cookies_path if self.use_cookies else None
        
        selected_format = None
        if self.quality_combo.isEnabled() and self.quality_combo.currentIndex() > 0:
            selected_format = self.quality_combo.currentData()
            self.log_view.append(f"[配置] 选择清晰度: {self.quality_combo.currentText()}")
            self.log_view.append(f"[调试] 实际使用 format key: {selected_format}")
        
        self.max_workers = self.concurrent_spin.value()
        
        self.worker = DownloadThread(
            cleaned_url, self.output_dir, download_type,
            cookies_path, selected_format, self.max_workers
        )
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._handle_result)
        self.worker.start()

    def _update_progress(self, current, total, percent, video_title):
        self.progress.setValue(percent)
        self.progress.setFormat(f"({current}/{total}) {video_title[:20]}... - {percent}%")

    def _handle_result(self, success, message):
        self.progress.setVisible(False)
        self.download_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.log_view.append("[成功] 下载已完成，请检查保存路径")
        else:
            error_msg = f"[严重错误] {message}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_view.append(error_msg)


class ToolWindow(BilibiliDownloader):
    def __init__(self, parent=None):
        super().__init__()
        self.return_to_toolbox = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BilibiliDownloader()
    window.show()
    sys.exit(app.exec())