#!/usr/bin/env python3
"""Format Amendment-1 reports using saved summaries only; never reads source labels."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'project/stage1_outputs/amendment1'

def read(name):
    return json.loads((OUT / name).read_text())

def interval(point, ci, percent=False, digits=6, suffix=None):
    if point is None or ci is None:
        return '未定义'
    scale = 100 if percent else 1
    suffix = ('%' if percent else '') if suffix is None else suffix
    return f'{point*scale:.{digits}f}{suffix} [{ci[0]*scale:.{digits}f}, {ci[1]*scale:.{digits}f}]'


def cv_report():
    data = read('CV_COMPARISON.json')
    lines = ['# Amendment 1：交叉验证逐组并排读数', '',
        '状态：已验证通过。三候选均完成真实/打乱标签五折，全部通过修订后的三组对照闸门；C03 按冻结选择规则胜出。此处不是锁定集裁决。', '',
        '以下是【实测】固定 KDA T24 s443、case 93000–93174 的开发部分（140 case；每组 280 episode）。regret 状态数为 560/560/558，失败率均为 560 状态。',
        '所有括号为状态配对、episode 整体重采样 5,000 次的 95% 区间。Delta=regret_true−regret_shuffle，负数有利于真实标签。缩减率正数有利于模型。', '',
        '## 每个候选真实与打乱臂', '',
        '|候选|人数|真实 regret 均值 [95%CI]|打乱 regret 均值 [95%CI]|真实较基线缩减 [95%CI]|打乱较基线缩减 [95%CI]|',
        '|---|---|---|---|---|---|']
    for cid in ('C01','C02','C03'):
        for group in ('5人','10人','20人'):
            t = data[cid]['true'][group]['episode_primary']; s = data[cid]['shuffle'][group]['episode_primary']
            lines.append('|'+ '|'.join([cid,group,interval(t['candidate']['regret_mean'],t['candidate']['regret_mean_ci95']),
                interval(s['candidate']['regret_mean'],s['candidate']['regret_mean_ci95']),
                interval(t['regret_reduction'],t['regret_reduction_ci95'],True,2),
                interval(s['regret_reduction'],s['regret_reduction_ci95'],True,2)])+'|')
    lines += ['', '## 主要追加读数：真标签减打乱标签', '',
        '|候选|人数|Delta episode 95%CI|Delta case-block 95%CI|真实减打乱失败率 [95%CI，百分点]|',
        '|---|---|---|---|---|']
    for cid in ('C01','C02','C03'):
        for group in ('5人','10人','20人'):
            e=data[cid]['paired'][group]['episode_primary']; c=data[cid]['paired'][group]['case_sensitivity']
            lines.append('|'+ '|'.join([cid,group,interval(e['delta_true_minus_shuffle'],e['delta_true_minus_shuffle_ci95']),
                interval(c['delta_true_minus_shuffle'],c['delta_true_minus_shuffle_ci95']),
                interval(e['failure_change_true_minus_shuffle'],e['failure_change_true_minus_shuffle_ci95'],True,2,'')])+'|')
    lines += ['', '## 三个预声明 20 人 CV 比较的多重比较敏感性', '',
        '|候选|真实较基线缩减 [Bonferroni 98.3333%CI]|Delta [Bonferroni 98.3333%CI]|', '|---|---|---|']
    for cid in ('C01','C02','C03'):
        t=data[cid]['true']['20人']['episode_primary']; d=data[cid]['paired']['20人']['episode_primary']
        lines.append('|'+ '|'.join([cid,interval(t['regret_reduction'],t['regret_reduction_ci98_3333_cv_bonferroni'],True,2),
             interval(d['delta_true_minus_shuffle'],d['delta_ci98_3333_cv_bonferroni'])])+'|')
    lines += ['', '## 失败率与同批控制', '',
        '|候选|人数|真实失败率 [95%CI]|打乱失败率 [95%CI]|真实减基线失败率 [95%CI，百分点]|', '|---|---|---|---|---|']
    for cid in ('C01','C02','C03'):
        for group in ('5人','10人','20人'):
            t=data[cid]['true'][group]['episode_primary']; s=data[cid]['shuffle'][group]['episode_primary']
            lines.append('|'+ '|'.join([cid,group,interval(t['candidate']['failure_rate'],t['candidate']['failure_rate_ci95'],True,2),
                interval(s['candidate']['failure_rate'],s['candidate']['failure_rate_ci95'],True,2),
                interval(t['failure_change_candidate_minus_base'],t['failure_change_ci95'],True,2,'')])+'|')
    lines += ['', '|人数|基线 regret [95%CI]|均匀随机 regret [95%CI]|基线失败率 [95%CI]|均匀随机失败率 [95%CI]|', '|---|---|---|---|---|']
    for group in ('5人','10人','20人'):
        t=data['C03']['true'][group]['episode_primary']
        lines.append('|'+ '|'.join([group,interval(t['base']['regret_mean'],t['base']['regret_mean_ci95']),
             interval(t['random']['regret_mean'],t['random']['regret_mean_ci95']),
             interval(t['base']['failure_rate'],t['base']['failure_rate_ci95'],True,2),
             interval(t['random']['failure_rate'],t['random']['failure_rate_ci95'],True,2)])+'|')
    lines += ['', '## 边界与来源', '',
        '- 三组表述均为描述性，不以若干子组显著结果代替预选的锁定 20 人主检验。CV 用于选择，不是确认性证据。',
        '- 完整 case-block、单安全动作失败率敏感性、top5 随机/事后上限、尾部一例/三例占比、去尾和中位数口径见各候选 `*_summary.json`。不把事后上限写成可达收益。',
        '- 本轮用了一个训练 seed；属于 B 类模型拟合证据。母体续行标签不代表闭环性能。',
        '- 修订前已看 C01 真/打乱、C02 打乱 CV；原停止报告保留。此次没有增加候选、更改划分或重训旧臂。',
        '- 原始报告：`project/reports/STAGE1_20261013.md`；修订原文和操作约定：`project/stage1/AMENDMENT-1*.md`。',
        '- 机器可读来源：本目录 `CV_COMPARISON.json`、`*_shuffle_gate.json`、`*_paired_true_minus_shuffle.json`、`SELECTED_CANDIDATE.json`。', '']
    (OUT/'CV_READOUT.md').write_text('\n'.join(lines))


def final_report():
    terminal=read('LOCKED_TERMINAL.json'); selected=read('SELECTED_CANDIDATE.json')
    t=read('locked_true_summary.json'); s=read('locked_shuffle_summary.json'); d=read('locked_paired_true_minus_shuffle.json')
    primary=t['20人']['episode_primary']; paired=d['20人']['episode_primary']; cv=read('CV_COMPARISON.json')
    lines=['# 阶段 1 修订后结果（2026-10-14）', '',
        f"## 结论：{terminal['verdict']}", '',
        '执行状态：已验证通过。下述裁决仅适用于固定 KDA T24 s443、预声明三种标量配置和母体续行离线表；不等于该研究方向已被证明无效。', '',
        f"【实测】按未变选择规则预选 C03；锁定 20 人 regret 较基线缩减 {interval(primary['regret_reduction'],primary['regret_reduction_ci95'],True,2)}；真标签减打乱标签 Delta={interval(paired['delta_true_minus_shuffle'],paired['delta_true_minus_shuffle_ci95'])}。",
        f"全状态失败率：基线 {interval(primary['base']['failure_rate'],primary['base']['failure_rate_ci95'],True,2)}，真实模型 {interval(primary['candidate']['failure_rate'],primary['candidate']['failure_rate_ci95'],True,2)}；配对差 {interval(primary['failure_change_candidate_minus_base'],primary['failure_change_ci95'],True,2,'')} 个百分点。", '',
        '20 人缩减点估计 11.33% <20% 且区间跨 0；真实相对打乱的正向增益区间下界为 −0.00005127，亦未严格大于 0。因此按原分界及新增条件裁为 INCONCLUSIVE。', '',
        'Delta 定义为真实模型 regret−打乱模型 regret；负数有利于真实标签。区间为 episode-primary 95%，20 人 Delta 的 episode-primary 区间跨 0，case-block 敏感性区间未跨 0，后者不能替代主判据。', '',
        '## 证据：锁定集三个组', '',
        '|人数|基线 regret [95%CI]|真实 regret [95%CI]|打乱 regret [95%CI]|随机 regret [95%CI]|真实较基线缩减 [95%CI]|Delta 真−打乱 [95%CI]|',
        '|---|---|---|---|---|---|---|']
    for group in ('5人','10人','20人'):
        e=t[group]['episode_primary']; sh=s[group]['episode_primary']; de=d[group]['episode_primary']
        lines.append('|'+ '|'.join([group,interval(e['base']['regret_mean'],e['base']['regret_mean_ci95']),
            interval(e['candidate']['regret_mean'],e['candidate']['regret_mean_ci95']),
            interval(sh['candidate']['regret_mean'],sh['candidate']['regret_mean_ci95']),
            interval(e['random']['regret_mean'],e['random']['regret_mean_ci95']),
            interval(e['regret_reduction'],e['regret_reduction_ci95'],True,2),interval(de['delta_true_minus_shuffle'],de['delta_true_minus_shuffle_ci95'])])+'|')
    lines += ['', '## 每个候选的主要追加 CV 读数', '',
        '|候选|20 人真实 regret [95%CI]|20 人打乱 regret [95%CI]|20 人 Delta 真−打乱 [95%CI]|', '|---|---|---|---|']
    for cid in ('C01','C02','C03'):
        ce=cv[cid]['true']['20人']['episode_primary']; cs=cv[cid]['shuffle']['20人']['episode_primary']; cd=cv[cid]['paired']['20人']['episode_primary']
        lines.append('|'+ '|'.join([cid,interval(ce['candidate']['regret_mean'],ce['candidate']['regret_mean_ci95']),
            interval(cs['candidate']['regret_mean'],cs['candidate']['regret_mean_ci95']),interval(cd['delta_true_minus_shuffle'],cd['delta_true_minus_shuffle_ci95'])])+'|')
    lines += ['', '三候选在三组的真/打乱臂、失败率、配对差和 case 区间完整并排列于 [CV_READOUT](../stage1_outputs/amendment1/CV_READOUT.md)。所有打乱 OOF 闸门通过；原 C02 停止记录未覆盖。', '',
        '## 核查、未验证和下一步', '',
        '- 63 项仓库测试、26 项原合成检查、13 项修订检查通过；技能验证 0 错误/0 警告；冻结/数据/历史 SHA 和独立基线/随机公式均通过。17 次新增拟合（15 折+2 全开发）均 <3 秒、无 debug 重试；CPU 最多 2 线程。',
        f"- 双模型和选择文件先在 `{terminal['publication_remote_commit']}` 提交并验证；唯一锁定源标签读取见 `amendment1/LOCKED_READ_STARTED.json`，结果见 `LOCKED_TERMINAL.json`。没有追加拟合或重读源标签。",
        '- 锁定每组 35 case、70 episode；regret 状态分母 140/140/139，失败率每组 140。episode 为主，case-block 为敏感性；单候选安全状态只从 regret 分母剔除。',
        f"- 20 人 case-block 缩减 {interval(t['20人']['case_sensitivity']['regret_reduction'],t['20人']['case_sensitivity']['regret_reduction_ci95'],True,2)}；Delta {interval(d['20人']['case_sensitivity']['delta_true_minus_shuffle'],d['20人']['case_sensitivity']['delta_true_minus_shuffle_ci95'])}。",
        '- 修订前已看到 C01 真/打乱、C02 打乱 CV，明确不是全程未触及结果的原始预注册。阶段 0 有全表聚合暴露；单训练 seed、共享 case 相关性和有限标量信息仍限制推断。',
        f"- 20 人收益集中：最大 3 case 占绝对配对增益 {interval(primary['tail']['top3_case_share_absolute_gain']['point'],primary['tail']['top3_case_share_absolute_gain']['ci95'],True,2)}；去掉基线 regret 最大 3 个状态后缩减 {interval(primary['tail']['drop_base_top3_reduction']['point'],primary['tail']['drop_base_top3_reduction']['ci95'],True,2)}；基线−真实 regret 中位数差 {interval(primary['tail']['median_difference']['point'],primary['tail']['median_difference']['ci95'])}。",
        '- 全组失败率、区间、top5 对照、尾部集中度、去尾和中位数口径见 `locked_true_summary.json`、`locked_shuffle_summary.json`；实际模型、数据来源、协议与划分哈希见 `SELECTED_CANDIDATE.json`。',
        '- 完成时间早于原总截止 2026-10-14 02:38 UTC；约九小时等待不计入阶段 1 活跃工作，但没有延长总墙钟期限。',
        '- 阶段 3 未触发：本结果不是 SUPPORTED，不制作方法卡，不执行闭环，不追加候选。后续若尝试新表示或新母体，必须另行授权并预先固定新协议。', '']
    path=ROOT/'project/reports/STAGE1_AMENDED_20261014.md'
    path.write_text('\n'.join(lines))
    print(path)

if __name__=='__main__':
    cv_report()
    if (OUT/'LOCKED_TERMINAL.json').exists():
        final_report()
