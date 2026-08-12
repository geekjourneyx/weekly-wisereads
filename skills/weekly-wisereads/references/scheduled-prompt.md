# Scheduled prompt

使用 `$weekly-wisereads` Skill 执行本次独立运行；不要依赖创建任务时的聊天历史。

仓库：`geekjourneyx/weekly-wisereads`
首页：`https://wise.readwise.io/`
方法定义：`skills/weekly-wisereads/SKILL.md`

## 权威规则

你不是在写 AI 周报。Weekly Wisereads 是 Readwise 用户上一周高亮人数最多的内容集合，主题完全由当期内容决定。AI / Agent / Harness / 工程只是可选分析镜头，不设配额；若没有显著相关内容，必须明确写出“本期无显著 AI / Agent / 工程信号”。每次都要区分高亮热度、内容质量、证据强度与样本偏差，且不得把 curated / partnered ebook 说成按高亮人数排名。

执行时必须遵守仓库 Skill 与 references，尤其是：

- `references/positioning-contract.md`
- `references/inventory-contract.md`
- `references/analysis-method.md`
- `references/evidence-policy.md`
- `references/report-template.md`
- `references/quality-gates.md`
- `references/readme-update-contract.md`
- `references/atomic-publish-protocol.md`

## 发现阶段

1. 先访问 `https://wise.readwise.io/`，确认最新一期是否更新。
2. 只以首页所见最新一期或 special edition 为准，进入详情页后确定 `issue_key / issue_kind / issue_number / issue_label / source_url`。
3. 如果首页与详情页无法稳定识别同一期，立即停止，不做任何仓库写入。
4. 读取仓库已有报告，按 `issue_key` 主去重、按 canonical `source_url` 次去重；若已处理，返回 no-op。
5. 冻结完整 `IssueInventory`：逐条记录顺序、类型、作者、URL、selection basis 与 `detail_page_item_count`，不得存储源全文。

## 研究阶段

1. 对每个条目完成原文深读；若受限，按证据策略降级到 `PARTIAL / ALTERNATE / SUMMARY_ONLY / UNAVAILABLE`。
2. 每个条目必须产出一个 terminal SourceCard，且只能在全部条目进入终态后再做跨条目综合。
3. 不得因为读者定位而强行生成 AI、创业、商业模式等栏目；主题必须从当期内容涌现。
4. 明确区分：作者观点、已证实内容、项目推断、待验证内容。
5. 对当期样本偏差给出具体观察：偏向了什么、缺了什么、会造成什么后果。

## 输出阶段

1. 按 `references/report-template.md` 生成完整中文 Markdown 报告。
2. 报告必须包含固定 front matter、固定章节顺序、AI 信号槽、`<!-- source-item:item-.. -->` 锚点、逐条阅读笔记、偏差分析、行动建议与来源说明。
3. 重点识别：
   - 值得理解、值得质疑、值得长期保留的观点；
   - 产品 / 商业 / 工程 / AI 机会（仅当内容实际支持时）；
   - 引发深度思考的文章与观点，不限于 AI，也包括人生、工作、财富、生活等。
4. 若当期没有相关 AI / Agent / 工程材料，保留该信号槽并写出精确缺席句，不得强行关联。

## 验证与写入

1. 先验证 inventory、report，以及仓库级规则；任何 hard gate 失败都停止且不写 GitHub。
2. 通过后，构建三文件 `PublicationPlan`：
   - 新报告文件
   - `reports/README.md`
   - 根 `README.md`
3. 只有在需要写仓库时，才按照 `references/atomic-publish-protocol.md` 的原子流程写入 `main`。
4. 写入后必须回读三个目标文件，校验 `issue_key`、canonical URL、归档顺序与提交 SHA。
5. 若并发运行导致其他流程先发布同一期，返回 no-op，不得重复创建第二份状态。

## 明确禁止

- 不得写死或猜测期号、发布日期、详情页 URL；每次只从实时首页第一期开始。
- 不得发明独立高亮人数、排名数据或任何来源未公开的数字。
- 不得访问、推断或披露任何私人 Readwise 数据；只使用公开网页与仓库中已公开的元数据。
- 不得写入 `geekjourneyx/weekly-wisereads` 之外的仓库。
- 不得创建 Issue、Pull Request、Release、Discussion 或社交媒体内容。
- 不得 force update、force push、改写历史或删除历史报告。
- 不得修改根 README 的 `AUTO:LATEST` 与 `AUTO:RECENT` 区块之外内容。

## 每次运行最终返回

返回结构化总结，至少包含：

- `issue_key`
- `source_url`
- `state`
- `report_path`
- `coverage`
- `ai_signal`
- `degraded_items`
- `quality_gate_findings`
- `published_commit_sha`
- `notes`
