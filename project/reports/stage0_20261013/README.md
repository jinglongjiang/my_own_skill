# 阶段 0 证据索引

基线：`dd1ea89a18599a0cd01484097561248f9acb590a`。主报告：[`../STAGE0_20261013.md`](../STAGE0_20261013.md)。

执行顺序：
1. 按要求依次阅读 `project/SITUATION.md`、`project/DATA.md`、`project/DOTS_BRIEF.md`、`shared/evidence-rules.md`，然后阅读仓库说明和待执行脚本。
2. 运行 `python3 tests/test_tools.py`，63 项、0 失败，退出码 0。
3. 运行 `python3 tools/validate.py`，12 个技能、0 错误、0 警告，退出码 0。
4. 原样运行任务书 target 命令，退出码 0。
5. 原命令仅追加 `--json-out project/reports/stage0_20261013/kda_s443_target.reproduced.json`，用于全精度逐值比较，退出码 0。
6. 比较全部 JSON 键、列表长度和数值叶节点：59 个数值中 2 个不一致，比较器退出码 1。立即停止后续验收。

原始命令、标准输出和退出码分别保存于 `logs/`。测试的临时合成数据及编译缓存均重定向到本证据目录下的 `runtime/`，由本目录 `.gitignore` 排除，不作为交付内容。没有新增安装依赖、后台定时任务或仓库外写入。

## 无须重跑统计的复核命令

在仓库根执行：

```bash
python3 project/reports/stage0_20261013/compare_results.py \
  project/results/kda_s443_target.json \
  project/reports/stage0_20261013/kda_s443_target.reproduced.json \
  --target-path-prefix
```

预期退出码 1；两个差异与 `target_comparison.json` 相同。Decimal 数值比较不设置容差；仅允许任务书路径迁移造成的 `files[0]` 从 `data/kda_s443_cf/table.jsonl.gz` 变为 `project/data/kda_s443_cf/table.jsonl.gz`，该非数值变化仍在输出中明列。

## 文件说明

- `kda_s443_target.reproduced.json`：本轮未改统计脚本生成的完整 JSON。
- `compare_results.py`：逐值比较脚本，仅读取给定 JSON、输出比较结果。
- `target_comparison.json`：完整比较结果。
- `logs/environment.log`：目标提交、分支、UTC 时间、Python/NumPy 版本及临时目录设置。
- `logs/test_tools.log`、`logs/validate.log`：第一闸门的完整输出。
- `logs/target_brief.log`：任务书原样命令及完整输出。
- `logs/target_export.log`：仅追加输出选项的命令及完整输出。
- `logs/target_comparison.log`：比较命令、完整输出及退出码。
- `logs/integrity.log`：已有 tracked 文件不变的 Git 检查；不等价于尚未进行的 MANIFEST SHA256 校验。

未执行 rescue、MANIFEST 校验、KDARL 代码读取和任何阶段 1 工作。全部差异的原因仍未验证。
