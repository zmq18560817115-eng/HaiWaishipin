# 本地知识库（零外部数据起步）

MVP 不依赖 NAS、飞书或 MySQL。Step 3 知识检索会读取本目录 Markdown。

## 已有内容

| 文件 | 用途 |
|------|------|
| `products/panda-bubu-pro.md` | 产品 FAB、试跑白名单参考 |
| `processes/海外短视频合规禁词.md` | 禁词与改写方向 |

## 你可以补充（可选）

- 把公司 FAB、商品说明复制为新的 `.md` 放到 `products/`
- 把合规文档放到 `processes/`
- 多个目录可在 `.env` 的 `KNOWLEDGE_RESEARCH_ROOT` 用 `;` 分隔追加

**规则**：知识库只作 B4 检索证据，不能自动扩大 `allowed_claims_en` 白名单。
