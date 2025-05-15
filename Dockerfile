FROM python:3.10-windowsservercore

WORKDIR /app

# 安装依赖
RUN pip install PyQt6==6.6.1 pyinstaller

# 复制项目文件
COPY . .

# 设置默认命令
CMD ["pyinstaller", "timer.spec"] 