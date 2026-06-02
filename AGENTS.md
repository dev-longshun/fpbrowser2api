# fpbrowser2api AGENTS 指令

## 项目基础信息

- **技术栈**：Python 3.10、FastAPI、Playwright CDP、SQLite、Roxy Browser 指纹浏览器、本地静态管理后台。
- **最低支持版本**：Python 3.10.x。
- **项目定位**：将已登录的指纹浏览器会话封装为 OpenAI 兼容的视频/图片生成 API，并通过后台管理项目、浏览器服务器、空间、窗口、任务类型与额度。

## 项目结构

- `main.py`：服务启动入口，并包含 Dreamina/Seedance 区域 URL patch。
- `src/api/`：FastAPI 路由与管理端接口。
- `src/core/`：配置、数据库、鉴权、模型、路径与日志基础设施。
- `src/services/`：任务调度、Roxy Browser 适配、Playwright CDP 上下文、各站点执行器与 OSS 上传等业务逻辑。
- `static/`：本地管理后台页面与前端资源。
- `config/`：运行配置示例与本地配置。
- `data/`：SQLite 数据库与运行数据。
- `.claude/skills/`：Claude Code 项目操作 skills，包括 `manage`、`deploy`、`video` 以及本次新增开发协议。
- `.codex/skills/`：Codex 项目级开发协议入口。
- `.cursor/skills/` 与 `.kiro/steering/`：Cursor / Kiro 对应协议入口。

## Skills

Skill 是存放在 `SKILL.md` 中的一组本地指令。

### 可用 Skills

- `protocol-dev`：高级技术架构师开发协议，强制执行“先谋后动”工作流，覆盖代码修改、Bug 调试、Commit 信息生成、分支合并、版本发布等流程。Codex 入口文件位于 `./.codex/skills/protocol-dev/SKILL.md`。
- `repo-detach-reset`：克隆/Fork 仓库去关联与历史重置协议，用于切断原仓库连接、重建 git 历史、清理 README 与工作流部署链路。Codex 入口文件位于 `./.codex/skills/repo-detach-reset/SKILL.md`。

### Skills 使用规则

- 触发规则：当用户提出代码修改、Bug 调试、生成 Commit 信息、分支合并/同步、文档更新、版本发布需求时，必须启用 `protocol-dev`。
- 触发规则：当用户提出抹除克隆仓库信息、删除历史提交、切断 upstream/origin、重建 git 仓库、清理 README、禁用或隔离原工作流/部署链路时，必须启用 `repo-detach-reset`。
- 显式触发：当用户明确提到 `protocol-dev`（`$protocol-dev` 或纯文本）时，必须启用该 skill。
- 显式触发：当用户明确提到 `repo-detach-reset`（`$repo-detach-reset` 或纯文本）时，必须启用该 skill。
- 作用范围：skill 默认只作用于当前轮对话，除非用户再次提及。
- 文件缺失：若 skill 文件不可读，先简要说明问题，再按最接近的流程继续执行。

### Skill 加载策略

- 仓库去关联类需求优先读取 `./.codex/skills/repo-detach-reset/SKILL.md`。
- 代码修改、调试、commit、发布类需求优先读取 `./.codex/skills/protocol-dev/SKILL.md`。
- 同时命中多个 skill 时，按任务主目标选择最小必要集合；若涉及破坏性仓库操作并伴随代码修改，先执行 `repo-detach-reset` 再执行 `protocol-dev`。
- `SKILL.md` 引用 `references/` 时，只按当前任务加载必要文件，不要一次性全量读取。
- 本文件只定义 Codex 入口规则；具体执行约束以对应 `SKILL.md` 为准。

## fpbrowser2api 项目约束

- Python 版本必须是 3.10.x；本项目包含发布用 `.pyc`，不要在普通开发任务中随意重生成或提交字节码。
- 启动服务前必须先执行 `unset all_proxy`，防止 HTTPX / Playwright 代理环境导致 `socksio` 相关错误。
- 每次涉及服务启动或 Dreamina/Seedance 站点链路时，都要检查日志中是否出现 `[region-patch] Patched 4 Dreamina URLs`。
- Roxy Browser 是 GUI 应用；远程部署需要 Windows RDP 或 Linux VNC 等桌面环境。
- Roxy Browser dashboard 标签页会导致 Playwright CDP 挂起；打开窗口后必须检查并关闭 dashboard 标签页。

## 开发协议关键约束

- 任何代码变更需求，必须先给方案，等待用户明确授权后才能执行。
- 仓库去关联/重置类破坏性操作（如删除历史、切断 remote）必须先给方案，明确风险与回滚点，等待用户授权后执行。
- 克隆仓库 DIY 时必须先做 License 检查；许可证义务不明确时默认不删除许可证与版权声明。
- 去关联操作必须隔离原工作流与部署链路，禁止将部署任务误触发到原作者仓库或原命名空间。
- 禁止使用 `rm` 删除文件，必须使用 `trash`。
- `git commit` 流程：先输出 commit 信息供用户审核，用户确认后再执行提交，提交内容必须与展示内容完全一致，禁止附加任何辅助编程标识信息（如 Co-Authored-By 等）。
- 禁止使用 Markdown 表格。
- `git worktree` 规范：新建 worktree 时，必须将工作树创建在项目同级目录下，目录名格式为 `{项目名}--{分支名}`（分支名中的 `/` 替换为 `-`）。例如项目为 `fpbrowser2api`，分支为 `feat/login`，则 worktree 路径为 `../fpbrowser2api--feat-login/`。禁止使用默认的 `.git/worktrees` 或项目内部路径。
