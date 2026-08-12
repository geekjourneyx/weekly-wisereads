# README 自动更新契约

本契约定义 Weekly Wisereads 发布阶段对根 `README.md` 受管区块和 `reports/README.md` 归档页的唯一允许写法。

## 受管标记

根 `README.md` 必须且只能各包含一组如下标记：

```html
<!-- AUTO:LATEST:START -->
<!-- AUTO:LATEST:END -->
<!-- AUTO:RECENT:START -->
<!-- AUTO:RECENT:END -->
```

规则：

- `AUTO:LATEST` 与 `AUTO:RECENT` 都必须恰好出现一对 `START` / `END`。
- 标记必须平衡，禁止缺失、重复、交叉或嵌套。
- 任何异常都必须 fail-closed；发布构建器直接报错，不得猜测修复。
- 标记外的 README 字节必须原样保留。

## 最新一期区块

`AUTO:LATEST` 仅渲染一行列表项：

```md
- [Vol. 155｜Wisereads Vol. 155 深度解读](reports/2026/2026-08-12-vol-155.md)
```

渲染规则：

- 使用最新一期的 `issue_label`、`title` 和仓库内报告路径。
- 链接路径相对仓库根，因此以 `reports/...` 开头。
- 区块正文不包含额外说明、标题或第二条列表项。

## 近期归档区块

`AUTO:RECENT` 渲染：

1. 最新到最旧的最近 6 期列表；
2. 一个空行；
3. 指向完整归档的固定入口：

```md
- [完整归档](reports/README.md)
```

当历史不足 6 期时，只列出现有期数。

## 完整归档页

`reports/README.md` 是完整历史索引，固定头部如下：

```md
# 报告归档

按发布时间倒序排列所有已发布报告。
```

其后跟随空行与完整列表，按最新到最旧排序，每行格式为：

```md
- [Vol. 155｜Wisereads Vol. 155 深度解读](2026/2026-08-12-vol-155.md)
```

归档页链接路径相对 `reports/README.md`，因此不带前缀 `reports/`。

## 排序与身份

- 排序主键为 `discovered_at` 倒序。
- 同一时间戳时按 `issue_number` 倒序，再按报告路径升序，确保稳定输出。
- 仓库历史与待发布报告必须以 `issue_key` 去重，并以规范化后的 `source_url` 二次去重。
- `source_url` 规范化规则为保留合法 issue URL，并统一为带尾随 `/` 的 canonical 形式。
- 发现重复身份时必须报错，不得静默覆盖或生成第二份状态。

## 发布计划输出

发布构建器必须一次性返回且只返回三个目标文件内容：

- 新报告文件；
- `reports/README.md`；
- 根 `README.md`。

构建器是纯函数式规划步骤：

- 读取仓库当前文件；
- 计算三个输出；
- 不写 GitHub；
- `--json` dry run 只输出路径、`issue_key` 与 canonical `source_url`，不得回显报告正文。
