# Decentralized Structural-RNN for Robot Crowd Navigation with Deep Reinforcement Learning

- ID: arXiv:2011.04820v4 (2025 revision read); ICRA 2021, pp.3517–3524.
- Role: near-miss / partial-observation baseline; reading: full.
- Full text: https://arxiv.org/pdf/2011.04820
- Author code/publication record: https://github.com/Shuijing725/CrowdNav_DSRNN

## Mechanism and assumptions

**Sec. III-A/C, Eqs. (1)–(7):** human input is position only, excluding velocity/radius. Shared spatial edge RNN, robot temporal RNN, attention and node RNN produce PPO actor/value outputs.

**Sec. IV-A:** humans use ORCA and cannot see/respond to the robot. FoV varies by angle, fixed within an episode; out-of-view humans are propagated using last observed velocity. Five humans start/finish on a 6m circle. Separate Group environments use 360° FoV and 10/15/20 humans, some static. This is angular missingness; geometric line-of-sight occlusion is not specified.

**Sec. IV-B:** DS-RNN and RNN+Attn train for 10 million steps. Six conditions use 500 unseen cases each. Other baselines follow their original training protocols.

## Published numbers

**Table I**, average time in successful episodes, seconds:

| Method | FoV90° | FoV180° | FoV360° | Group20 |
|---|---:|---:|---:|---:|
| DS-RNN | 11.83 | 10.99 | 11.79 | 15.52 |
| RNN+Attn | 16.57 | 14.00 | 10.96 | 25.55 |
| RGL | 9.54 | 9.48 | 9.59 | 16.44 |

Success/collision results are in Figs.5–6; no bar values are transcribed without readable figure verification. Independent training-seed count and CIs are unreported.

**Sec. VI:** invisible-robot realism, noisy detection and fixed crowd-size generalization remain limitations.

## Public code verification

[config.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_DSRNN/main/crowd_nav/configs/config.py), browser raw-text lines L27–65, L119–123:
- circle_radius=6; human_num=5; humans.policy=orca
- robot.visible=False; robot.FOV=2π default, configurable for experiments
- humans.random_unobservability=False; humans.random_policy_changing=False
- training.num_env_steps=10e6

Author README provides trained holonomic/unicycle examples and a FoV configuration workflow. Current main is not a frozen publication release; availability is verified, executability/reproduction unverified.

## Relevance

【推论】Good angular-FoV temporal-memory baseline. Neither hidden responsive types nor geometric occlusion should be inferred from “partial observability.” Group20 and FoV90° are separate conditions, not evidence for a 20-person narrow-FoV result. Successful-only time can favor methods that fail difficult episodes; retain outcome rates when reproducing.
