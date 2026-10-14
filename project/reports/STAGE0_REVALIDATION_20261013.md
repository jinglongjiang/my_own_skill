# 阶段 0：按用户修订容差重新验收

## 结论

**已验证通过（前三项本地闸门；暂用标量路线）。**【实测】工具测试、target、rescue 和 MANIFEST 全部通过；采用本轮用户明确授权的规则：整数严格相等，浮点绝对差不超过 `1e-9`。13 维及 8 槽位定义仍为 **未验证**，按用户允许的后备方案不使用 NPZ 特征；不声称第四项已通过。原严格逐值报告保留为历史证据，本报告不把旧标准下的失败改写成通过。

## 证据

- 【实测】2026-10-13 16:39–16:42 UTC；基线本地提交 `cf85574`；Python 3.12.14、NumPy 2.3.5。`tests/test_tools.py`：63 项，失败 0；`tools/validate.py`：12 个技能，错误 0、警告 0。见 [环境](stage0_revalidation_20261013/logs/environment.log)、[测试](stage0_revalidation_20261013/logs/test_tools.log)、[校验](stage0_revalidation_20261013/logs/validate.log)。
- 【实测】[target 比较](stage0_revalidation_20261013/target_comparison.json)：8 个整数严格一致，51 个浮点全部通过；仅两项非零差 `+2e-16`、`−1e-16`，与历史失败位置相同。路径元数据仅允许已记录的 `project/` 前缀差异。[rescue 比较](stage0_revalidation_20261013/rescue_comparison.json)：9 个整数、36 个浮点全部严格一致。[新比较器](stage0_revalidation_20261013/compare_results.py) 保留 int/float 类型并拒绝类型变化；11 项合成测试覆盖整数差异、容差边界、相对大数、非有限值、结构差异。
- 【实测，A 类】冻结 KDA T24 s443、case 93000–93174：20 人基线 regret `0.1096`，随机 `0.1196`；相对随机消除率 `8.377%`，95% 区间 `[−6.925%, 23.247%]`。后续失败 `116/700`，失败率 `16.57% [12.86%, 20.57%]`；随机安全动作 `17.26% [14.32%, 20.46%]`；失败中可救比例 `54.31% [44.28%, 64.81%]`。均为母体续行下的事后查表量，不是可达增益。完整三组数值：[target](stage0_revalidation_20261013/kda_s443_target.reproduced.json)、[rescue](stage0_revalidation_20261013/kda_s443_rescue.reproduced.json)。
- 【实测】[MANIFEST 校验](stage0_revalidation_20261013/manifest_verification.json)：7/7 文件 SHA256 与字节数一致。表 SHA256 `3e4f137d86455e1db9e496420f365a0713e6f8b9f0bb3f6c99649aec07d5a5a2`；MANIFEST SHA256 `0bd2428d061665ac9d89c34e02553d53b73da697322161ce33d57d15ecc72993`。NPZ 仅哈希原始字节，未解码。已有数据及已有结果无变更。

## 没做的和不确定的

**未验证**：外部 KDARL 源码定义，因仓库外操作仍待批准；源索引和母体权重不在本仓库，不能重新计算其 SHA。未拟合模型、未读取 NPZ 数组、未开展文献或闭环实验。阶段 0 按任务书对全表做聚合复现，未来锁定集不能声称完全没有历史聚合暴露；本轮没有按结果筛选拆分或查看候选模型的锁定成绩。未读取、生成或索取 case 90000–90199、92000–92499。

## 下一步建议

推荐先提交本报告，再冻结仅用可用标量的分组拆分和候选协议，随后建模。另一方案是等待 KDARL 只读许可完成特征定义，但不可猜测槽位含义。阶段 1 的拆分、候选清单及标签打乱硬停止规则须在拟合前提交；提交确认前不进入拟合。
