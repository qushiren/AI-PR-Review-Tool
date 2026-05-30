# AI PR 代码评审工具

AI PR 代码评审工具帮助开发者更快、更稳定地完成 GitHub Pull Request 评审。它会获取指定 PR，解析代码变更，总结变更意图，识别风险代码，并生成可以在本地查看或回写到 GitHub 的 Review 建议。

## 支持能力

- 按文件和风险领域汇总 PR 变更。
- 识别密钥泄露、SQL 注入模式、鉴权相关改动、宽泛异常捕获、危险命令执行、依赖变更、生成文件和大规模 diff 等风险。
- 生成带有严重级别、置信度、影响文件、影响行号、证据和修复建议的 Review 建议。
- 可选 OpenAI 模型分析，并向模型提供紧凑的、包含仓库上下文的变更信息包。
- 提供 FastAPI 服务、浏览器 UI 和 CLI 工作流。
- 可选将 Markdown 格式的 Review 评论发布到 PR 会话中。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

在 `.env` 中设置 `GITHUB_TOKEN`。`OPENAI_API_KEY` 是可选项；如果未配置，工具会运行确定性的本地分析器。

运行 CLI：

```bash
ai-pr-review review https://github.com/owner/repo/pull/123
```

运行 Web API 和 UI：

```bash
uvicorn ai_pr_review_tool.api:app --reload
```

打开 `http://127.0.0.1:8000`。

发布 PR 评论：

```bash
ai-pr-review review https://github.com/owner/repo/pull/123 --post-comment
```

## 配置

| 变量 | 是否必需 | 说明 |
| --- | --- | --- |
| `GITHUB_TOKEN` | 是 | 具备仓库读取权限的 GitHub token。若要发布评论，需要增加写权限。 |
| `OPENAI_API_KEY` | 否 | 启用模型辅助评审。 |
| `OPENAI_MODEL` | 否 | 默认值为 `gpt-4.1-mini`。 |
| `AI_REVIEW_MAX_PATCH_CHARS` | 否 | 发送给分析流程的最大 patch 字符预算。 |

## 设计说明

关于模型选择、上下文获取、误报控制、速度取舍和扩展路线，请查看 [docs/DESIGN.md](docs/DESIGN.md)。

## 开发

```bash
pytest
ruff check .
```
