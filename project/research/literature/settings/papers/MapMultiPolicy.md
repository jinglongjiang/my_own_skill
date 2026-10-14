# Crowd-Aware Robot Navigation for Pedestrians with Multiple Collision Avoidance Strategies via Map-based Deep Reinforcement Learning

- ID: arXiv:2109.02541; IROS 2021, pp.8144–8150; DOI 10.1109/IROS51168.2021.9636579.
- Role: near-miss with an important exclusion boundary; reading: full.
- Primary text: https://arxiv.org/pdf/2109.02541
- Author-related simulator: https://github.com/DRL-Navigation/img_env
- Training framework linked there: https://github.com/DRL-Navigation/DDRL4NAV

## Mechanism and actual setting

**Sec. IV-A, Fig.1:** PPO uses a sensor map, three-channel pedestrian map (location,vx,vy), and robot target pose. No human policy-label input is specified. Differential-drive controls; discrete variant has 28 actions.

**Sec. IV-B:** four parallel training environments cross random/circular layouts with ORCA/SFM human policies. Each contains two policy-sharing robots and four pedestrians; random layout also has four static obstacles.

**Sec. V-B2:** explicitly avoids mixing ORCA and SFM pedestrians **within one environment**, because human-human collisions would confound testing. Thus “multiple strategies” means training across different environments, not demonstrated hidden per-person policy types within a mixed crowd. Exact robot-to-human observation interface remains unverified.

## Published evaluation

**Table II**, 500 environments per scenario; success / extra successful-navigation time:

| Scenario | PPO-PSD | Sensor-only PPO-SD |
|---|---|---|
| Random, ORCA humans | .936 / 4.83s | .856 / 3.60s |
| Random, SFM humans | .968 / 4.99s | .840 / 3.45s |

No independent-training-seed count or CIs reported. No paired significance claim. **Sec. V-C/VI:** real corridor failures remain; broader strategy generalization is future work.

## Code check and interpretation

Simulator README explicitly cites this IROS paper and gives a `yao2021crowd` reproduction workflow using DDRL4NAV and ped_map configuration. Repository existence and author linkage verified; exact policy observation/response implementation and runnable status were not audited.

【推论】Useful counterexample to title-only screening: a multi-policy title does not establish a simultaneously heterogeneous hidden-type crowd. Keep as related training-distribution work, not the strongest answer to question A. Sensor-map sensing is not enough to assert a particular simulated geometric occlusion or dropout model.
