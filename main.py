import sys
import json
import os
import time
import threading
import hashlib
import tempfile
import urllib.request
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QComboBox, QLabel, QPushButton, 
                            QCheckBox, QFrame, QScrollArea, QMessageBox,
                            QProgressDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

# 版本信息
VERSION = "1.0.0"
UPDATE_CHECK_URL = "https://yolindung.github.io/perfect-timer-updates/version.json"

def calculate_md5(file_path):
    """计算文件的MD5值"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def download_file(url, progress_dialog):
    """下载文件并显示进度"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as temp_file:
            response = urllib.request.urlopen(url)
            total_size = int(response.headers['Content-Length'])
            downloaded_size = 0
            
            progress_dialog.setMaximum(total_size)
            
            while True:
                buffer = response.read(8192)
                if not buffer:
                    break
                    
                downloaded_size += len(buffer)
                temp_file.write(buffer)
                progress_dialog.setValue(downloaded_size)
                
            return temp_file.name
    except Exception as e:
        QMessageBox.critical(None, "下载错误", f"下载文件时出错：{str(e)}")
        return None

def check_for_updates():
    """检查更新"""
    try:
        response = urllib.request.urlopen(UPDATE_CHECK_URL)
        data = json.loads(response.read())
        if data['version'] > VERSION:
            return True, data['version'], data['download_url'], data.get('release_notes', ''), data.get('release_date', ''), data.get('md5', '')
    except:
        pass
    return False, None, None, None, None, None

class FloatWindow(QWidget):
    _instances = []  # 用于跟踪所有悬浮窗实例
    _base_position = QPoint(100, 100)  # 初始位置
    _offset = 30  # 窗口之间的偏移量

    def __init__(self, name, time, parent=None, on_all_closed=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.name = name
        self.time = time
        self.current_time = time
        self.old_pos = None
        self.on_all_closed = on_all_closed  # 新增：关闭回调
        self.init_ui()
        self.set_position()
        FloatWindow._instances.append(self)

    def set_position(self):
        # 计算新窗口的位置
        index = len(FloatWindow._instances) - 1
        x = FloatWindow._base_position.x() + (index * FloatWindow._offset)
        y = FloatWindow._base_position.y() + (index * FloatWindow._offset)
        self.move(x, y)

    def closeEvent(self, event):
        # 从实例列表中移除
        if self in FloatWindow._instances:
            FloatWindow._instances.remove(self)
        # 新增：所有悬浮窗关闭时通知主窗口
        if not FloatWindow._instances and self.on_all_closed:
            self.on_all_closed()
        super().closeEvent(event)

    def init_ui(self):
        self.setFixedSize(100, 100)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # 顶部横向布局：名称+关闭按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        
        # 名称标签
        name_label = QLabel(self.name)
        name_label.setFont(QFont("华文楷体", 12))
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_label.setStyleSheet("""
            QLabel {
                color: white;
                border: none;
                background: transparent;
            }
        """)
        top_layout.addWidget(name_label)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 80, 80, 200);
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgb(255, 0, 0);
                color: #fff;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_layout.addStretch()  # 添加弹性空间，将按钮推到右边
        top_layout.addWidget(close_btn)
        layout.addLayout(top_layout)

        # 时间标签
        self.time_label = QLabel(str(self.current_time))
        self.time_label.setFont(QFont("Microsoft YaHei", 60, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                color: white;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(self.time_label)
        layout.addStretch()

        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 179);  /* 黑色背景，透明度70% */
                border: none;
                border-radius: 20px;
            }
        """)

    def update_time(self, time):
        self.current_time = time
        self.time_label.setText(str(time))
        if time <= 3:
            self.time_label.setStyleSheet("""
                QLabel {
                    color: red;
                    border: none;
                    background: transparent;
                }
            """)
        else:
            self.time_label.setStyleSheet("""
                QLabel {
                    color: white;
                    border: none;
                    background: transparent;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

class TimerWindow(QFrame):
    def __init__(self, name, time, description, parent=None, on_all_float_closed=None):
        super().__init__(parent)
        self.name = name
        self.time = time
        self.description = description
        self.current_time = time
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.float_window = None
        self.on_all_float_closed = on_all_float_closed
        self.init_ui()

    def init_ui(self):
        # 创建主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)  # 设置组件之间的间距
        
        # 设置固定高度
        self.setFixedHeight(100)  # 固定计时器容器高度
        
        # 左侧时间显示容器
        time_container = QWidget()
        time_container.setFixedWidth(80)  # 减小宽度
        time_container.setStyleSheet("""
            QWidget {
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        time_layout = QVBoxLayout()
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_container.setLayout(time_layout)
        
        self.time_label = QLabel(str(self.current_time))
        self.time_label.setFont(QFont("Microsoft YaHei", 40, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: rgba(240, 240, 240, 200);
                border: none;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        time_layout.addWidget(self.time_label)
        main_layout.addWidget(time_container)
        
        # 中间信息区域
        info_container = QWidget()
        info_container.setFixedWidth(250)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)  # 减小名称和描述之间的间距
        info_layout.setAlignment(Qt.AlignLeft)  # 设置左对齐
        info_container.setLayout(info_layout)
        
        # 名称标签
        name_label = QLabel(self.name)
        name_label.setFont(QFont("华文楷体", 30, QFont.Weight.Bold))
        name_label.setFixedWidth(200)
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
        """)
        info_layout.addWidget(name_label)
        
        # 介绍标签
        desc_label = QLabel(self.description)
        desc_label.setFont(QFont("华文楷体", 14))
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        desc_label.setMinimumHeight(40)  # 设置最小高度
        desc_label.setStyleSheet("""
            QLabel {
                line-height: 200%;  /* 设置2倍行间距 */
                background-color: transparent;  /* 移除背景色 */
            }
        """)
        info_layout.addWidget(desc_label)
        
        main_layout.addWidget(info_container)
        
        # 右侧按钮区域
        button_container = QWidget()
        button_container.setFixedWidth(80)  # 增加容器宽度
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_container.setLayout(button_layout)
        
        # 开始按钮
        self.start_button = QPushButton("开始")
        self.start_button.setFixedSize(70, 35)  # 增加按钮尺寸
        self.start_button.clicked.connect(self.toggle_timer)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc47a;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 16px;  /* 增加字体大小 */
            }
            QPushButton:hover {
                background-color: #3aa55a;
                filter: brightness(1.1);
            }
        """)
        button_layout.addWidget(self.start_button)
        
        # 复位按钮
        self.reset_button = QPushButton("复位")
        self.reset_button.setFixedSize(70, 35)  # 增加按钮尺寸
        self.reset_button.clicked.connect(self.reset_timer)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #ff5c5c;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 16px;  /* 增加字体大小 */
            }
            QPushButton:hover {
                background-color: #d90000;
                filter: brightness(1.1);
            }
        """)
        button_layout.addWidget(self.reset_button)
        
        main_layout.addWidget(button_container)
        
        self.setLayout(main_layout)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 128);
                border: none;
                border-radius: 10px;
                margin: 2px;
            }
        """)

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.current_time = self.time  # 停止时显示预设值
            self.update_display()
            self.start_button.setText("开始")
        else:
            self.current_time = self.time - 1  # 启动时从预设值-1开始
            self.update_display()
            self.timer.start(1000)
            self.start_button.setText("停止")

    def reset_timer(self):
        self.timer.stop()
        self.current_time = self.time
        self.update_display()
        self.start_button.setText("开始")

    def update_time(self):
        if self.current_time > 0:
            self.current_time -= 1
        else:
            self.current_time = self.time - 1  # 循环时也从预设值-1开始
        self.update_display()

    def update_display(self):
        self.time_label.setText(str(self.current_time))
        if self.current_time <= 3:
            self.time_label.setStyleSheet("color: red")
        else:
            self.time_label.setStyleSheet("")
        
        if self.float_window:
            self.float_window.update_time(self.current_time)

    def show_float_window(self):
        if not self.float_window:
            self.float_window = FloatWindow(self.name, self.current_time, on_all_closed=self.on_all_float_closed)
            self.float_window.show()

    def hide_float_window(self):
        if self.float_window:
            self.float_window.close()
            self.float_window = None

class MainWindow(QMainWindow):
    def __init__(self):
        self.float_windows_enabled = False
        super().__init__()
        self.init_ui()
        self.load_timers()

    def init_ui(self):
        self.setWindowTitle("完美世界国服经典版副本计时器")
        self.setFixedSize(480, 854)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        layout.setSpacing(10)  # 设置垂直间距为10px
        layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐
        main_widget.setLayout(layout)
        
        # 设置标题
        title_label = QLabel("《完美世界国服经典版》\n副本计时器")
        title_label.setFont(QFont("华文楷体", 40, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFixedHeight(120)  # 固定标题高度
        layout.addWidget(title_label)
        
        # 创建菜单容器
        menu_container = QWidget()
        menu_container.setFixedHeight(40)  # 固定菜单高度为40px
        menu_layout = QHBoxLayout()
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_container.setLayout(menu_layout)
        
        # 创建一级菜单
        self.level1_combo = QComboBox()
        self.level1_combo.currentIndexChanged.connect(self.update_level2)
        menu_layout.addWidget(self.level1_combo)
        
        # 创建二级菜单
        self.level2_combo = QComboBox()
        self.level2_combo.currentIndexChanged.connect(self.update_timers)
        menu_layout.addWidget(self.level2_combo)
        
        layout.addWidget(menu_container)
        
        # 创建全局控制按钮容器
        control_container = QWidget()
        control_container.setFixedHeight(40)  # 固定控制按钮高度为40px
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_container.setLayout(control_layout)
        
        # 创建按钮组
        button_group = QHBoxLayout()
        button_group.setSpacing(20)  # 设置按钮之间的水平间距
        self.start_all_button = QPushButton("全部启动")
        self.start_all_button.clicked.connect(self.start_all_timers)
        self.start_all_button.setStyleSheet("""
            QPushButton {
                background-color: orange;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #ff8800;
                filter: brightness(1.2);
            }
        """)
        self.reset_all_button = QPushButton("全部复位")
        self.reset_all_button.clicked.connect(self.reset_all_timers)
        self.reset_all_button.setStyleSheet("""
            QPushButton {
                background-color: orange;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #ff8800;
                filter: brightness(1.2);
            }
        """)
        self.float_checkbox = QCheckBox("数字悬浮")
        self.float_checkbox.stateChanged.connect(self.toggle_float_windows)
        button_group.addWidget(self.start_all_button)
        button_group.addWidget(self.reset_all_button)
        button_group.addWidget(self.float_checkbox)
        
        # 添加弹性空间使按钮组居中
        control_layout.addStretch()
        control_layout.addLayout(button_group)
        control_layout.addStretch()
        
        layout.addWidget(control_container)
        
        # 创建计时器容器（可滚动区域）
        self.timer_container = QWidget()
        self.timer_layout = QVBoxLayout()
        self.timer_layout.setSpacing(15)  # 将计时器之间的间距设置为15px
        self.timer_layout.setContentsMargins(5, 15, 5, 0)  # 设置左右边距为5px，上边距为15px
        self.timer_layout.setAlignment(Qt.AlignTop)  # 设置顶部对齐
        self.timer_container.setLayout(self.timer_layout)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.timer_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(scroll_area)

    def load_timers(self):
        try:
            with open('timers.json', 'r', encoding='utf-8') as f:
                self.timer_data = json.load(f)
                self.level1_combo.addItems(self.timer_data.keys())
        except Exception as e:
            print(f"Error loading timers: {e}")

    def update_level2(self):
        self.level2_combo.clear()
        current_level1 = self.level1_combo.currentText()
        if current_level1 in self.timer_data:
            self.level2_combo.addItems(self.timer_data[current_level1].keys())
        self.update_timers()

    def update_timers(self):
        # 关闭所有悬浮窗并取消复选框选择
        self.float_checkbox.setChecked(False)
        self.float_windows_enabled = False
        
        # 清除现有计时器
        while self.timer_layout.count():
            item = self.timer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新计时器
        current_level1 = self.level1_combo.currentText()
        current_level2 = self.level2_combo.currentText()
        
        if current_level1 in self.timer_data and current_level2 in self.timer_data[current_level1]:
            timers = self.timer_data[current_level1][current_level2]
            # 适配dict和list两种结构
            if isinstance(timers, dict):
                for name, data in timers.items():
                    timer = TimerWindow(name, data["时间"], data["介绍"], on_all_float_closed=self.on_all_float_closed)
                    timer.setFixedHeight(100)  # 设置固定高度
                    self.timer_layout.addWidget(timer)
                    if self.float_windows_enabled:
                        timer.show_float_window()
            elif isinstance(timers, list):
                for data in timers:
                    name = data.get("name", "计时器")
                    time = data.get("time", 60)
                    desc = data.get("description", "")
                    timer = TimerWindow(name, time, desc, on_all_float_closed=self.on_all_float_closed)
                    timer.setFixedHeight(100)  # 设置固定高度
                    self.timer_layout.addWidget(timer)
                    if self.float_windows_enabled:
                        timer.show_float_window()

    def start_all_timers(self):
        for i in range(self.timer_layout.count()):
            timer = self.timer_layout.itemAt(i).widget()
            if isinstance(timer, TimerWindow) and not timer.timer.isActive():  # 只启动未运行的计时器
                timer.toggle_timer()

    def reset_all_timers(self):
        for i in range(self.timer_layout.count()):
            timer = self.timer_layout.itemAt(i).widget()
            if isinstance(timer, TimerWindow):
                timer.reset_timer()

    def toggle_float_windows(self, state):
        self.float_windows_enabled = state == Qt.Checked
        for i in range(self.timer_layout.count()):
            timer = self.timer_layout.itemAt(i).widget()
            if isinstance(timer, TimerWindow):
                if self.float_windows_enabled:
                    timer.show_float_window()
                else:
                    timer.hide_float_window()

    def on_all_float_closed(self):
        self.float_checkbox.setChecked(False)

    def check_updates(self):
        """检查更新"""
        has_update, new_version, download_url, release_notes, release_date, expected_md5 = check_for_updates()
        if has_update:
            message = f'发现新版本 {new_version}\n'
            if release_date:
                message += f'发布日期：{release_date}\n'
            if release_notes:
                message += f'\n更新内容：\n{release_notes}\n'
            message += '\n是否下载更新？'
            
            reply = QMessageBox.question(
                self,
                '发现新版本',
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 创建进度对话框
                progress = QProgressDialog("正在下载更新...", "取消", 0, 100, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.setWindowTitle("下载进度")
                progress.setAutoClose(True)
                progress.setAutoReset(True)
                
                # 下载文件
                temp_file = download_file(download_url, progress)
                if temp_file:
                    # 验证MD5
                    actual_md5 = calculate_md5(temp_file)
                    if actual_md5.lower() == expected_md5.lower():
                        # 打开下载目录
                        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(temp_file)))
                        QMessageBox.information(
                            self,
                            "下载完成",
                            f"新版本已下载完成，文件保存在：\n{temp_file}\n\n请关闭当前程序后安装新版本。"
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "校验失败",
                            "文件校验失败，下载可能不完整或已被篡改。\n请重新下载或联系开发者。"
                        )
                        os.remove(temp_file)

    def showEvent(self, event):
        """窗口显示时检查更新"""
        super().showEvent(event)
        # 在新线程中检查更新，避免阻塞UI
        threading.Thread(target=self.check_updates, daemon=True).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 