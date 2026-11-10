# communication-basics

18 个高频职场沟通场景的 AI 教练：话术模板 + AI 陪练 + 能力测评。

## 功能亮点

- **18 个高频沟通场景**：识人、破冰、倾听、回应、接好任务、请教求助、同步汇报、回应批评、会议发言、澄清提问、发表不同意见、说服他人、给TA建议、为TA点赞、进度催办、主动道歉、学会拒绝、处理冲突
- **四条核心路径**：直接用（场景话术模板）、想学（沉浸式学习）、陪我练（AI 角色扮演陪练 + 五维评分）、测测我（沟通能力诊断测评）
- **知识卡片**：18 张场景方法卡片（`assets/` 目录内置 PNG），一键展示核心方法
- **数据回写框架**：陪练评分/练习记录/反馈可回写数据库，内置评分单位校验与双重加权自动还原

## 安装

将本仓库整体复制到你的 Agent skills 目录（如 OpenClaw 的 `~/.openclaw/skills/`），目录名保持 `communication-basics`：

```bash
git clone https://github.com/your-name/communication-basics.git ~/.openclaw/skills/communication-basics
```

Agent 会根据 `SKILL.md` 中的触发词（怎么说、怎么汇报、怎么拒绝、陪我练、测测我等）自动调用。

## Setup 注意事项

1. **课程视频/文稿链接**：默认不含课程视频与文稿链接（`references/lesson-lookup.md` 中为占位符）。如有自己的课程资源，可在该表中补充链接。
2. **数据回写为可选功能**：陪练评分回写依赖 `scripts/db_helper.py`，需自行在脚本顶部配置数据库地址（支持 PostgREST 风格 REST API）和 API key（默认为 `TODO_YOUR_DB_URL` 占位符）。未配置时，Skill 的对话、陪练、学习功能不受影响，仅数据回写不可用。
3. **知识卡片图片已内置**：18 张卡片 PNG 位于 `assets/lesson-01.png` ~ `assets/lesson-18.png`，无需额外下载。

## License

[MIT](LICENSE)
