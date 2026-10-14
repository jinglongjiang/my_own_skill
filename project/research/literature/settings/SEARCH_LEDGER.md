# Settings literature search ledger

- Started 2026-10-14 02:13 UTC after QUESTION_FREEZE.md.
- Sources: public web search, arXiv full texts, author/project pages and public GitHub source views.
- Scope: questions 2/3 only; mechanisms for action ranking delegated elsewhere.
- No login, signup, project-data submission, paid/gated downloading, API literature scripts, code execution or user-browser access.
- Outputs restricted to `project/research/literature/settings/`.
- Inclusion/exclusion criteria unchanged from QUESTION_FREEZE.md. Full reading means method, settings, evaluation and limitations checked with at least two location anchors. Public availability is not reproducibility.

## Executed queries (18)

| # | Exact query | Useful discovery / result |
|---:|---|---|
| 1 | crowd robot navigation partially observable field of view occlusion heterogeneous human policies visible robot paper | PaS, partial-observation candidates |
| 2 | crowd navigation robot visible humans hidden intentions ORCA policy types uncertainty paper | SARL, MapMultiPolicy, HI Robot; several broad surveys |
| 3 | crowd navigation "hidden" "types" robot | No stronger specific early result; many irrelevant hidden-state uses |
| 4 | crowd navigation "heterogeneous" "policies" robot visible | HEIGHT, H2INT discovery snippets |
| 5 | "Crowd-Aware Robot Navigation for Pedestrians with Multiple" code | MapMultiPolicy primary PDF |
| 6 | "Decentralized Structural-RNN" crowd navigation FOV | DS-RNN author site/arXiv |
| 7 | crowd navigation "unknown" "cooperation" human robot policy paper | Trautman 2013, multisubject cooperation material |
| 8 | crowd navigation "latent" "cooperativeness" robot published code | Weak direct results; non-navigation partner modeling excluded |
| 9 | "Crowd-Aware Robot Navigation" "Yao" github | DRL-Navigation/img_env, author reproduction linkage |
| 10 | "crowd navigation" "Liu" "moving forward" ORCA 2020 2021 | Liu IROS2020 discovered through references, no full text obtained in pass |
| 11 | "Robot Navigation in Crowded Environments Using Deep Reinforcement Learning" pdf | Broader listings; no selected full text |
| 12 | "crowd" "hidden" "policy" "robot" "type" navigation POMDP | HICN-AS; H2INT snippets; driving POMDPs outside scope |
| 13 | "Learning to Socially Navigate" "Interaction Capacity" arxiv | Qiu et al. 2022 acoustic interaction paper |
| 14 | Lucia Liu Dugas Cesari navigation crowded environments 2020 arxiv | NavRep and secondary lists; exact primary unavailable in this pass |
| 15 | "Learning Selective Acoustic Signaling" authors | HICN-AS publisher identity/date metadata |
| 16 | "Robot Navigation" "Crowded Environments" "Liu" github | Other author repositories; no substitute for exact primary |
| 17 | "Learning Selective Acoustic Signaling" github | Publisher result, no verified author implementation |
| 18 | "HICN-AS" code | Mostly unrelated namesakes; no verified author implementation |

## Screening and reading decisions

| Candidate | Source | Decision / role | Reading | Reason / boundary |
|---|---|---|---|---|
| HEIGHT | https://arxiv.org/html/2411.12150v4 | Include near-miss / baseline | full + author code | Responsive/nonresponsive generated types; observation exclusion and geometry verified. T-ASE publication checked. |
| PaS | https://arxiv.org/pdf/2210.00552 | Include near-miss / baseline | full + author config | Explicit geometric occlusion plus finite range. Exclude as evidence for responsive robot-visible humans. |
| DS-RNN | https://arxiv.org/pdf/2011.04820 | Include near-miss / baseline | full + author config | Explicit angular FoV, temporal model. Robot invisible; geometric occlusion not established. |
| MapMultiPolicy | https://arxiv.org/pdf/2109.02541 | Include near-miss, boundary example | full + code provenance | Multi-policy training across environments, explicitly not mixed ORCA/SFM within environment. |
| HICN-AS: Learning Selective Acoustic Signaling for Social Robot Navigation in Heterogeneous Crowds | https://www.mdpi.com/2075-1702/14/9/1011 | Exclude this round, do not cite method/metrics | title (publisher search-index excerpts only) | Search exposes Sec.3 and publication 2026-09-05, but full HTML/PDF consistently fail 429/internal error. Cannot satisfy full criterion. |
| Human-Human & Human-Robot Interaction Transformer (H2INT) | https://arxiv.org/abs/2609.05300 | Exclude this round | title (secondary discovery only) | Search snippets look close, but primary full text/publication status not checked; no mechanism claim made. |
| Robot Navigation in Crowded Environments Using Deep Reinforcement Learning, Liu et al. IROS2020 | Found in MapMultiPolicy references / listings | Exclude this round | title | Exact public full text not obtained in this bounded pass. |
| Learning to Socially Navigate in Pedestrian-rich Environments with Interaction Capacity | https://arxiv.org/abs/2203.16154 | Exclude this round | abstract | Acoustic communication adds action/modalities; stronger direct setting evidence found in HEIGHT. |
| What we see and What we don't see: Imputing Occluded Crowd Structures from Robot Sensing | https://arxiv.org/abs/2109.08494 | Exclude from navigation-method evidence | abstract | Imputation/prediction alone is not verified closed-loop navigation. |
| Robot Person Following Under Partial Occlusion | https://arxiv.org/abs/2302.02121 | Exclude | abstract | Person-following task, not crowd traversal to independent goal. |
| HI Robot: Human intention-aware robot planning for safe and efficient navigation in crowds | https://ieeexplore.ieee.org/document/7759511/ | Exclude this round | abstract | Potential blocker-type precedent, but full text not read; no method/number citation. |
| Robot Navigation in Dense Human Crowds: The Case for Cooperation | https://las.inf.ethz.ch/files/trautman13robot.pdf | Exclude this round | abstract (first-page indexed text) | Real responsive crowds relevant, but hidden-type equivalence not checked; no full note or method citation. |
| SICNav | https://ojs.aaai.org/index.php/AAAI/article/view/41408 | Exclude this round | abstract (reprint only) | Interactive ORCA planner; must locate original journal article before treating reprint as full publication evidence. |
| How Much Information Does a Robot Need? | https://www.mdpi.com/2078-2489/11/2/112 | Exclude this round | abstract | Sensor-range study relevant but lower priority than full code-linked papers. |
| ARPL | https://doi.org/10.1007/s44443-026-00785-5 | Exclude this round | title (search excerpt only) | Recent mixed OOD claim; published primary not read. No numbers used. |
| General HRI/partner-modeling, driving POMDPs, multi-robot capability papers | Queries 7/8/12 | Exclude from this subtask | title | Different task or no closed-loop crowd-navigation setting evidence. |

## Full-read anchors and author code

- HEIGHT: III-A/B; IV-B Eqs.4/8/10; V-A/B4; Table II/III; VII; Appendix B. Public source at https://github.com/Shuijing725/CrowdNav_HEIGHT. Detailed code trace in papers/HEIGHT.md.
- PaS: III ray tracing/robot invisibility; IV-A Eq.2; V setup; VI Table I; VII/VIII. https://github.com/yejimun/PaS_CrowdNav.
- DS-RNN: III-A/C Eqs.1–7; IV-A/B; Table I; VI limitations. https://github.com/Shuijing725/CrowdNav_DSRNN.
- MapMultiPolicy: IV-A/B; V-B2 Table II and explicit within-scene policy exclusion; V-C/VI. https://github.com/DRL-Navigation/img_env links its exact IROS reproduction to https://github.com/DRL-Navigation/DDRL4NAV.

## Backend/access and audit limits

- Author-hosted MapMultiPolicy PDF failed once; public arXiv PDF succeeded, used instead.
- PaS GitHub HTML config failed; public raw.githubusercontent.com config succeeded.
- GitHub Raw-button routes occasionally failed; normal public raw.githubusercontent.com pages succeeded. No authentication or security restriction bypassed.
- HICN-AS publisher main/htm/pdf returned 429/internal errors. Kept at title/excerpt level and excluded this round; no login or gated retrieval attempted.
- PDF screenshot calls returned only opaque image references through this tool route. DS-RNN figure-bar percentages not transcribed; Table I text remains verified.
- Current author main branches were read without cloning or executing; no paper-release commit pin obtained. Raw-page line labels are browser-text labels, explicitly marked in notes.
- No independent-seed count/CIs found in selected main navigation reports; no CIs reconstructed from rounded values.
- Search was time-bounded, not exhaustive. A paper excluded for incomplete reading could narrow the remaining gap; no novelty-by-absence inference is permitted.

## Final contradiction check

HEIGHT arena_size=4.5 initially looked inconsistent with the paper. Tracing `loadArena` and `collision_checker` in crowd_sim_tb2.py shows the added human position range and wall thickness; effective half-width is 6m. The suspected arena mismatch was withdrawn in notes and parent update. Dynamic-plus-static count, observation-noise defaults and action-unit discrepancies remain explicitly unverified rather than repaired by assumption.
