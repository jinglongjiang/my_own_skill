# KDARL 特征定义只读核查

核查时间：2026-10-14；公开 main 提交 `fd155a616fdb66d04c556c613821f68835755312`。状态：**已验证通过（该提交的代码定义）**；冻结 NPZ 与此代码版本的逐项来源对应仍为**未验证**。本轮不增加候选、不解码 NPZ、不改原三个标量候选。

## 8 个槽位与各槽位的 13 维

【代码事实】13 列的含义取决于槽位，不能给所有槽位套同一列名。数组先全零初始化。

| 槽位（从 0 计） | 13 列，按 0–12 排列 |
|---|---|
| 0 机器人 | px, py, vx, vy, radius, gx, gy, v_pref（原值）, theta, 到目标欧氏距离, 速度模长, clip(v_pref,0,3), 标识1 |
| 1 目标 | gx−px, gy−py, 到目标距离, atan2(目标相对y,目标相对x), cos(该角), sin(该角), 0,0,0,0,0,0,0 |
| 2 运动 | 速度模长, atan2(vy,vx), cos(运动角), sin(运动角), 0,0,0,0,0,0,0,0,0；速度≤1e−6 时前4列也置0 |
| 3–7 行人 | hx−px, hy−py, sqrt(相对x²+相对y²+1e−6), 行人绝对vx, 行人绝对vy, 行人速度模长, 行人半径, TTC倒数特征, 距离<2的标识, 0,0,0,0 |

来源：[contracts.py:398–511](https://github.com/jinglongjiang/KDARL/blob/fd155a616fdb66d04c556c613821f68835755312/CrowdNav/crowd_nav/contracts.py#L398-L511)，blob SHA `fa30df78c2df13b21ec0e3baa04569a58e8b101b`。

【代码事实】行人行的距离是中心距离（带1e−6），不是扣除半径的净距；其速度列是行人绝对速度，不是相对速度。TTC倒数使用闭合速度：正闭合时 1/max(dist/closing_speed,0.1)，不闭合为0，极小距离分支为10；这是中心距离构造的特征，不等同于精确碰撞时间。

## 行人来源、排序和窗口

【代码事实】[mamba_rl.py:734–752](https://github.com/jinglongjiang/KDARL/blob/fd155a616fdb66d04c556c613821f68835755312/CrowdNav/crowd_nav/policy/mamba_rl.py#L734-L752) 的 34 维构造先取输入 human_states 的前5个，不足零填充；随后 contracts.py:450–480 过滤全零行，并在这至多5个行人中按近似TTC排序填槽。排序分数为闭合速度>0.1时 dist/(closing+1e−6)，否则 dist×10。不能据此声称从全部20人中选择最危险5人；上游输入排序未在此核查。

【代码事实】[空间编码器:81–110](https://github.com/jinglongjiang/KDARL/blob/fd155a616fdb66d04c556c613821f68835755312/CrowdNav/crowd_nav/policy/mamba_rl.py#L81-L110) 读取槽0和3:8，对行人再按距离排序，派生相对速度等关系量。槽1/2虽存在于输入，不能因此断言该编码器直接读取它们。policy blob SHA `c2468571024302843e021acea99f3800b1c5690d`。

【代码事实】[候选窗口:793–874](https://github.com/jinglongjiang/KDARL/blob/fd155a616fdb66d04c556c613821f68835755312/CrowdNav/crowd_nav/policy/mamba_rl.py#L793-L874) 将当前帧加入实际历史，行人匀速推进一步，机器人按候选速度推进；前缀共享，最后一帧依候选变化，按 seq_len 截断，不足以首帧左填充。对应任务数据所述24步窗口时前缀23步。无需执行网络或仿真即可读取这些定义。

## 限制与本轮决定

【未验证】本仓库 MANIFEST 提供母体权重哈希和文件哈希，但未锁定生成标签所用 KDARL 源码提交；当前公开源码还包含动作0分数减1e−3等行为，不能据当前代码重写已冻结表。原始生成环境、上游行人筛选和 NPZ 各行数值对应未重验。本轮继续冻结标量路线，仅补齐代码解释；现有数据和判据不变。
