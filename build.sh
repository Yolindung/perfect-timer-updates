#!/bin/bash

# 构建 Docker 镜像
docker build -t perfect-timer-builder .

# 运行容器并打包程序
docker run --rm -v "$(pwd):/app" perfect-timer-builder

# 复制打包好的程序到更新服务器目录
cp dist/完美计时器.exe perfect-timer-updates/downloads/完美计时器_1.0.0.exe

# 计算 MD5
python3 -c "
import hashlib
def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

md5 = calculate_md5('perfect-timer-updates/downloads/完美计时器_1.0.0.exe')
print(f'MD5: {md5}')
"

# 更新 version.json
echo "请将上面显示的 MD5 值复制到 version.json 文件中" 