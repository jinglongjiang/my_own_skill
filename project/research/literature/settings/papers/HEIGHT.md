# HEIGHT: Heterogeneous Interaction Graph Transformer for Robot Navigation in Crowded and Constrained Environments

- ID: arXiv:2411.12150v4; DOI: 10.1109/TASE.2025.3646588
- Role: near-miss / settings baseline; reading: full
- Publication: IEEE T-ASE. Manuscript front matter gives publication 2025-12-15; author repository labels T-ASE 2026. Do not call it T-RO or merely a 2024 preprint.
- Primary text: https://arxiv.org/html/2411.12150v4
- Public author implementation: https://github.com/Shuijing725/CrowdNav_HEIGHT
- Checked: 2026-10-14. No execution or reproduction performed.

## Published method and setting

**Sec. III-A/B; IV-B, Eqs. (4), (8), (10):** separate human-human and robot-human attention, obstacle CNN, then GRU and PPO actor/critic. Inputs include detected human positions/velocities, robot state, and obstacle point cloud; human goals and responsiveness labels are absent. Real deployment omits human velocities. Static obstacle scans use a prebuilt map, avoiding human occlusion of that map.

**Sec. V-A:** 12×12m PyBullet arena; 5–9 humans, including 0–2 static; 8–12 rectangular obstacles. Dynamic humans use ORCA: 20% respond to the robot, 80% do not. Human speed 0.4–0.6m/s; robot differential-drive with 3×3 translational/rotational acceleration choices; 0.1s step; 491-step cap.

**Sec. V-B4, Appendix B1:** 2×10^8 training steps; same 500 unseen episodes; best test-success checkpoint among the final five reported. Independent training-seed count and confidence intervals are unreported.

## Published numbers, not our benchmark

Table II (success / collision / timeout; successful-episode time):

| Setting | HEIGHT | DS-RNN |
|---|---|---|
| 5–9 humans, 8–12 obstacles | .88 / .12 / .00; 18.31s | .80 / .20 / .00; 19.90s |
| 10–14 humans, 8–12 obstacles | .78 / .22 / .00; 19.69s | .76 / .22 / .01; 23.08s |

Rounded published values; no interval/pairwise significance claim. Table III's in-distribution full-model time differs (18.49s); keep tables separate.

**Sec. V-C4; VII-A/D:** sudden goal changes, blocked passages, speed limits, sim-to-real mismatch, and long-horizon limitations remain.

## Author-code verification

Read-only public main; **not pinned to a paper-release commit**. Locations below are function/symbol anchors; numeric ranges refer to the browser's raw-text line numbering, not guaranteed GitHub file line numbers.

1. [config.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_HEIGHT/main/crowd_nav/configs/config.py), raw L311–340: robot.visible=True, visible_prob=.2, FOV=2π. Raw L392–400: LiDAR range=25m. `utils/robot.py` assigns that range to robot.sensor_range.
2. [crowd_sim_var_human.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_HEIGHT/main/crowd_sim/envs/crowd_sim_var_human.py), `generate_circle_crossing_human`, raw L252–261: turtlebot dynamic humans receive one Bernoulli responsiveness draw **when generated**; static humans get False. This is not a per-step response resampling.
3. [crowd_sim.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_HEIGHT/main/crowd_sim/envs/crowd_sim.py), `get_human_actions`, raw L976–1012: responsive humans receive robot observable state when geometrically within human FOV; nonresponsive humans omit it.
4. [crowd_sim_tb2_obs.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_HEIGHT/main/crowd_sim/envs/crowd_sim_tb2_obs.py), `generate_ob`, raw L106–192: human features are position and optional velocity; no responsiveness flag. `ray_test_no_humans` removes humans for static-obstacle scan.
5. [crowd_sim_tb2.py](https://raw.githubusercontent.com/Shuijing725/CrowdNav_HEIGHT/main/crowd_sim/envs/crowd_sim_tb2.py), `ray_test`/`get_num_human_in_fov`, raw L288–394: PyBullet nearest ray hits determine detected human IDs. This is geometric occlusion, not random detection dropout.

## Interpretation and caveats

- 【代码事实】The checked implementation has persistent generated response types hidden from the robot observation, in addition to hidden goals. It directly establishes prior art for a **mixed** responsive/nonresponsive setting; it does not establish that all humans can see/respond to the robot.
- 【推论】It is a stronger settings neighbor than an ordinary hidden-goal CrowdNav paper. Its “heterogeneous graph” terminology itself refers to entity/edge categories; hidden responsiveness is an environment detail, not an explicit latent-type estimator.
- Current main uses dynamic human count 7±2 plus static 1±1, whereas the paper describes total 5–9 including static humans. Exact publication configuration remains unverified. Arena size is NOT a confirmed mismatch: `crowd_sim_tb2.py::collision_checker` raw L1065–1069 uses arena_size + human_pos_noise_range − .5 = 4.5 + 2 − .5 = 6m half-width. 【推论】This agrees with the paper’s 12m effective arena; reading arena_size alone would have been wrong.
- README reports a visualization synchronization bug and instructs evaluation with visualize=False. Code availability is verified; reproducibility is unverified.
- Fair reuse requires matching response-type sampling, observation geometry, map access, dynamics, training budget and checkpoint selection. No numerical comparison with KDA s443 is warranted.

Additional config check: raw `config.py` L436–444 sets humans.random_unobservability=False, humans.random_policy_changing=False and noise.add_noise=False in current main. The first flag concerns a human failing to observe other agents; it is not a robot detector dropout control. Paper Sec.III-A describes Gaussian observation noise, so current default equivalence is unverified here as well.

Action-unit audit: the paper Sec.III-A describes acceleration values and multiplication by Δt. Current `crowd_sim_tb2.py::set_action_space` (raw L160–167) defines .05/.1 velocity increments, and `step` (L794–796) adds them directly. Treat exact physical action equivalence as unverified until a publication configuration/version is pinned; do not change the paper wording to conceal this difference.
