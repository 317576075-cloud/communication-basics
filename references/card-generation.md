# 卡片生成规则

## 触发时机

1. 路径A：解决完眼前问题后，如果场景对应18讲中的某一讲
2. 路径B：每次学习结束时（必须生成）
3. 模块二 Step 6：用户选择「看知识卡片」时
4. 用户主动说「给我看卡片」「发张卡片」

## 生成步骤

18 张知识卡片已预先生成为高清 PNG 图片，包含在本仓库 `assets/` 目录中。

```
Step 1：根据场景名，直接在下方「卡片图片路径映射表」中定位对应行
Step 2：取出本地图片路径（assets/ 目录）
Step 3：按当前平台选择输出方式（见下方「按平台输出」）
```

> 视频链接需另查 `references/lesson-lookup.md`，卡片图片在本文件内即可完成查找。

## 卡片图片路径映射表

> 图片已包含在本仓库 assets/ 目录，随仓库分发，无需外网访问。
> 可直接按**场景名**定位本地图片路径，无需先查 lesson-lookup.md 获取 Lesson 编号。

| 场景 | Lesson | 本地图片路径 |
|------|--------|---------|
| 识人 | 01 | assets/lesson-01.png |
| 破冰 | 02 | assets/lesson-02.png |
| 倾听 | 03 | assets/lesson-03.png |
| 回应 | 04 | assets/lesson-04.png |
| 接好任务 | 05 | assets/lesson-05.png |
| 请教求助 | 06 | assets/lesson-06.png |
| 同步汇报 | 07 | assets/lesson-07.png |
| 回应批评 | 08 | assets/lesson-08.png |
| 会议发言 | 09 | assets/lesson-09.png |
| 澄清提问 | 10 | assets/lesson-10.png |
| 发表不同意见 | 11 | assets/lesson-11.png |
| 说服他人 | 12 | assets/lesson-12.png |
| 给TA建议 | 13 | assets/lesson-13.png |
| 为TA点赞 | 14 | assets/lesson-14.png |
| 进度催办 | 15 | assets/lesson-15.png |
| 主动道歉 | 16 | assets/lesson-16.png |
| 学会拒绝 | 17 | assets/lesson-17.png |
| 处理冲突 | 18 | assets/lesson-18.png |

## 按平台输出

**支持 Markdown 图片的平台**：
用 Markdown 图片语法直接内嵌输出，图片在对话中直接显示：

```
![知识卡片：{场景名}](对应的本地图片路径)
```

**支持带参数 Markdown 图片语法的平台**：
使用 `adaptive,preview` 参数可自适应宽度并支持点击预览：

```
![知识卡片：{场景名}]({图片路径} "adaptive,preview")
```

如果渲染失败或图片缺失，降级为纯文本卡片。

**纯文本降级**（图片缺失 或 平台确实无法发送图片时）：通过 `python3 scripts/content_query.py card --scenario {场景名}` 查询对应场景的卡片数据，用结构化文本输出：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📇 知识卡片：{场景名}

🎯 核心方法：{方法名}

{方法要点，逐条列出}

💡 一句话记住：{金句}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**卡片数据源**：`data/cards.json`（通过 `scripts/content_query.py card` 按需查询）

---

## ⚠️ 无Lesson编号场景的兜底规则

- 当前场景在 `lesson-lookup.md` 中无对应 Lesson 编号时，静默跳过卡片图片推送
- 直接输出纯文本知识摘要替代卡片（见上方「纯文本降级」格式）
- 不输出任何错误信息，不展示加载失败的图片占位符
- 此规则优先于任何"必须推卡片"的规则
