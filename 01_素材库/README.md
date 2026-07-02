# 01 素材库

| 子目录 | 内容 |
|--------|------|
| `竞品对标/数据表/` | TikTok 竞品 URL、元数据、8 字段结构拆解 CSV |
| `竞品对标/AI拆解结果/` | 每条对标 #{id} 的 analysis.json |
| `产品资料/` | 我方产品 Markdown + listing 图片（**白底主图 = AI 外观锚点**） |
| `人像角色/` | 已批准出镜角色三视图 + `characters.json` 元数据 |
| `脚本快照/` | 每次「生成脚本」的快照 script-pack.json（本地，默认不进 Git） |

## 产品 Listing 必备图（便携恒温杯示例）

```text
产品资料/便携恒温杯/listing-0602-nw/
  主图/白底主图.png       ← 外观唯一锚点；SeedDance 默认垫图
  主图/倒出口参考.png     ← 倾倒演示镜专用，不可替代白底主图
  M端/、副图/、A+/        ← 场景与细节参考
```

更新图片后：在**开发者本机** `git add` 并 `git push workflow main`；内网服务器**只** `git pull`，不在内网做 push。说明见 `README_使用说明.md` →「产品资料与 GitHub 同步」。

公司知识库引擎副本：`overseas-loc-mvp/knowledge/`（合规、流程、产品镜像）
