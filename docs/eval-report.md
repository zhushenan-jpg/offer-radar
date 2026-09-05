# JobPilot 评测报告

- 样本:n=12 | 本轮重评 0 条 | rubric v1.1 | model mimo-v2.5-pro
- **Spearman 相关:0.302**(模型排序与人工排序的一致性)
- **MAE:13.0**(平均绝对误差,百分制)
- **Top-3 重合率:0.67**

## 逐条对照

| 公司 | 职位 | 模型分 | 人工分 | 差值 |
|---|---|---|---|---|
| Airbnb |  Senior Machine Learning Engineer, P | 7.0 | 15.0 | -8.0 |
| Cloudflare |  Business Development Representative | 6.5 | 5.0 | +1.5 |
| Coinbase |  Staff Infrastructure Engineer, Trad | 20.0 | 17.0 | +3.0 |
| Databricks | 	Delivery Solutions Architect - Comm | 30.0 | 12.0 | +18.0 |
| Discord | Advertising Operations Manager | 12.0 | 6.0 | +6.0 |
| Dropbox | Account Executive | 13.0 | 5.0 | +8.0 |
| Duolingo | Ad Sales Lead - West | 10.0 | 4.0 | +6.0 |
| Pinterest | Administrative Business Partner I -  | 13.5 | 3.0 | +10.5 |
| Stripe |  Credit Risk Operations Associate | 2.0 | 9.0 | -7.0 |
| Figma | AI Applied Scientist | 9.5 | 60.0 | -50.5 |
| Cloudflare | Software Engineer Intern (Fall 2026) | 30.5 | 50.0 | -19.5 |
| Cloudflare | Software Engineer Intern (Fall 2026) | 32.5 | 50.0 | -17.5 |

## 校准(按模型分位桶看人工分均值)

| 模型分区间 | n | 模型均值 | 人工均值 |
|---|---|---|---|
| 0-25 | 9 | 10.4 | 13.8 |
| 25-50 | 3 | 31.0 | 37.3 |
| 50-75 | 0 | - | - |
| 75-100 | 0 | - | - |

## 说明与局限

- 本轮重评 0 条成功;
- 样本量小,数字用于 prompt/rubric 迭代的相对比较,不是统计结论;
- 人工标注存在主观性,多人标注取均值可降低方差(annotations 表按 annotator 区分);
- 证据引用逐字校验(evidence_validator)在评分时已强制执行。
