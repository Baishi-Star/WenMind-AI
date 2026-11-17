# 大模型与图片识别配置

## 识别提速建议

图片作文识别（`/essays/ocr`、`/student/submissions/{id}/transcribe`）与文字评价共用一套
OpenAI 兼容配置，但识别方向可以**独立指定模型**，不影响评价所用模型：

- `OCR_MODEL`：识别专用模型；留空则复用 `LLM_MODEL`
- `OCR_BASE_URL` / `OCR_API_KEY`：留空则复用 `LLM_BASE_URL` / `LLM_API_KEY`
- `OCR_TIMEOUT_SECONDS`：识别请求超时，默认 120 秒

推荐候选（按“照抄文字”场景的速度）：

| 模型 | 特点 | 适用 |
|---|---|---|
| `glm-4v-flash` | 免费、快，适合整页手写转写 | 识别首选 |
| `qwen-vl-plus` | 视觉稳定，速度中等 | 识别备选 |
| `deepseek-flash` | 推理型，质量高但单页可达 90–300 秒 | 文字评价可用，识别不推荐 |

配置示例（仅切换识别，不动评价模型）：

```dotenv
OCR_ENABLED=true
OCR_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OCR_API_KEY=xxx
OCR_MODEL=glm-4v-flash
OCR_TIMEOUT_SECONDS=120
```

## 参数说明

- `LLM_VISION_MAX_TOKENS`：识别输出上限，默认 4096。照抄文字任务通常足够；
  若使用推理型视觉模型，推理会消耗大量 token，需按模型上调（如 16384+），否则正文会被截断。
- 修改 `.env` 后必须重启后端（配置在进程启动时读取）。
- 前端上传前会压缩图片：最长边 ≤1600px、JPEG 质量 0.82，可显著降低视觉 token 与识别耗时。

## 注意事项

- `OCR_*` 名称是历史命名，实际调用视觉大模型，不使用本地 OCR 库。
- 识别结果仅供学生校对，提交时以学生确认文本为准，不直接作为评价证据。
- 生产环境不要把真实密钥写入前端或提交到仓库。