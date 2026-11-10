# WenMind AI 后端镜像
# 构建上下文：backend/
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 系统依赖：faiss/scikit-learn 运行时所需的 libgomp
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖，最大化利用构建缓存
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 再拷贝应用代码
COPY app ./app

EXPOSE 8000

# 运行数据（SQLite / 上传文件 / 向量索引）由外部卷挂载
VOLUME ["/app/data"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]