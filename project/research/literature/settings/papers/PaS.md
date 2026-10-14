# Occlusion-Aware Crowd Navigation Using People as Sensors

- ID: arXiv:2210.00552v3; role: near-miss / partial-observation baseline; reading: full
- Publication: ICRA 2023, confirmed by author repository.
- Primary text: https://arxiv.org/pdf/2210.00552
- Author implementation: https://github.com/yejimun/PaS_CrowdNav
- Checked 2026-10-14; no reproduction.

## Method, assumptions and environment

**Sec. III, Fig. 2:** robot-invisible simulation: humans influence each other but do not respond to the robot. Ray tracing marks cells behind detected agents unknown; partially occluded agents remain detectable. A circular “FOV” means **range**, not a restricted viewing angle.

**Sec. IV-A/B, Eq. (2):** pretrained ground-truth VAE supplies a latent target. A partial-observation encoder matches it; its representation and robot state feed an RNN PPO planner. Ground-truth map is training-only. Four observation maps cover one second. Reconstruction loss was dropped because navigation degraded.

**Sec. V:** six ORCA humans; radius [.3,.4)m, speed [.5,1.5)m/s; noisy 4m circle starts. Robot radius .3m, maximum speed 2m/s, acceleration 1m/s². Maps: 10×10m, .1m cells; sensing radius 3m. Training: 15 million steps; validation 100, testing 500 episodes.

## Published evaluation

**Table I:** success / collision / time / path:

| Method | Success | Collision | Time (s) | Path (m) |
|---|---:|---:|---:|---:|
| Seq-OBS-FE | .82 | .18 | 16.39 | 13.68 |
| PaS-VAE | .91 | .09 | 13.91 | 12.26 |
| Seq-GT-VAE oracle | .97 | .03 | 14.85 | 13.39 |

Table caption says timeouts “are not included”; it does not make the denominator convention sufficiently explicit here. Do not assume conditional renormalization. Independent training seeds and navigation uncertainty intervals are unreported. Rounded points cannot establish paired significance.

**Sec. VII/VIII:** Turtlebot demonstration; larger real-pedestrian datasets remain future work.

## Verified author-code facts

[config.py](https://raw.githubusercontent.com/yejimun/PaS_CrowdNav/main/crowd_nav/configs/config.py), browser raw-text lines:
- L20–24: circle_crossing; six humans.
- L27–28 and L49–59: ORCA, random_policy_changing=False, robot.visible=False, FOV=2π, FOV_radius=3.
- L45–47: random_unobservability=False. Its commented scope is blindness of a human, not random robot-detection dropout.
- L64: noise disabled. L81–85: .1m grid; sequence=4.
- Repository has simulation, PPO training and test instructions. Public code existence verified, current main not pinned; no run performed.

## Relevance

【推论】Direct precedent for geometric person-person occlusion plus finite range, with training-only privileged map supervision. Not evidence for robot-visible responsive-human navigation or hidden heterogeneous policy types. It changes representation and policy learning rather than reranking the repository's 80 actions. Its published rates belong only to its own six-human environment.
