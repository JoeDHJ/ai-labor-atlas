# AI task evidence and organizational design



Haojian Dui · College of Economics, Shenzhen University · AI Labor Atlas 0.6.1



## The question and answer



How should an organization choose AI workflows when indicators of occupational

exposure and observed platform use give different shortlists? This project connects

three distinct measurements to a task-allocation decision. Its empirical result is

descriptive: Microsoft Copilot applicability and task-linked Claude conversation

share correlate positively, but only 100 occupations appear in both sources' top

quartiles of 190 occupations each. The hypothetical organization case shows why

even a plausible AI task saving needs a separate review-capacity calculation.



The contribution is the connection between measurement and decision. Atlas aligns

legacy and current occupational codes, conserves released conversation share,

reports common-sample ranks and allocation sensitivity, reconstructs a published

score, and exposes an organization model's assumptions. The source indicators and

underlying studies are the work of their original authors. This project adds the

comparison, analytical implementation and decision case; it does not estimate a

new causal effect of AI on wages, employment or firm productivity.



## Table I. Source comparison



| Measurement | Economic object | Observation scope and unit |

| --- | --- | --- |

| AIOE | Potential exposure of occupational abilities to AI progress | Source SOC 2010 exposure, conservatively bridged to SOC 2018; raw source units |

| Microsoft v1.1 | Task applicability from activity coverage, classified completion and impact | US consumer Copilot, January–September 2024; detailed SOC 2018, score 0–1; O*NET 29.0 weights |

| Anthropic 2025-02-10 | Released conversation share associated with occupational task wording | Claude task aggregates; source CSV does not specify observation dates; percent of released task conversations |



Notes: The Anthropic release is deliberately a fixed historical benchmark, not the

latest Economic Index release. Platform populations, models, tasks and periods

differ. Consumer conversations can be outside paid work. Conversation percentages

are neither worker adoption rates nor shares of paid work hours. AIOE is a

potential-exposure measure. Microsoft's applicability is also informed by observed

consumer use; it is not an independent engineering capacity test. Thus the analysis

compares constructs rather than ranking sources by accuracy.



## Align the units before comparing ranks



The Anthropic accompanying task file contains legacy O*NET-SOC codes. Atlas follows

the official O*NET-SOC 2010 → 2019 crosswalk, then the official O*NET-SOC 2019 →

SOC 2018 crosswalk. It uses exact task wording after case folding and whitespace

normalization. It does not use fuzzy text matching or truncate legacy codes and

assume they describe a current occupation.



Let p(t) be the published percentage for task wording t and S(t) the set of distinct

target SOCs linked to that wording after both crosswalks. Define the allocated

conversation share u(s) = sum over t with s in S(t) of p(t)/|S(t)|. An occupation

does not gain extra weight because it has more O*NET child records. Equal allocation

across possible links is transparent but is an assumption; the data do not identify

the actual occupation of the person in a conversation. Summing across allocations

preserves the matched source share, and unmatched share remains visible.



Exactly 3,513 of 3,514 released task labels match. Matched allocations account for

99.5184% of the released conversation share; the source's `none` residual label

accounts for the remaining 0.4816%. The task

universe links 790 SOC occupations and Microsoft publishes 785. Their intersection

contains 758; 171 of these have no released matched task usage. A zero is used only

within this covered task universe. Occupations outside source coverage stay missing.

The 216 task labels with multiple target SOCs are divided across distinct targets.



Each source is ranked separately on the same intersection. Ties receive average

ranks, scaled from 0 to 100 using 100 × (rank − 1)/(N − 1). A percentile gap is a

descriptive difference in relative position, in percentage points. It does not

subtract the original source units or quantify unmet adoption.



## Table II. Common-sample descriptive results



| Sample / task allocation | SOC count | Spearman rank correlation |

| --- | ---: | ---: |

| Microsoft and Claude, fractional task allocation | 758 | 0.617 |

| Same sources, only occupations with positive released task use | 587 | 0.488 |

| Same 758 occupations, only single-target task wording retained | 758 | 0.539 |

| AIOE and Microsoft, three-source intersection | 692 | 0.696 |

| AIOE and Claude, three-source intersection | 692 | 0.676 |



Notes: Occupations are equally weighted. The zero-use restriction changes the

sample; the single-target restriction changes the task allocation on the same

sample. Neither is an independent validation sample. The three-source comparison

excludes 66 of the public pair's occupations because local AIOE coverage is missing.

Individual AIOE values remain local, with public output limited to aggregate results.

These statistics describe released aggregates; no standard errors or causal inference

are claimed. Exact values, the third pair on the same 692 occupations, and all public

occupation rows are in `measurement-comparison.json`.



The public pair's mean absolute percentile gap is 19.64 points. Only 100 of 190

top-quartile picks overlap, or 52.6% of either shortlist. This incomplete overlap

matters when capacity allows only a small number of workflow pilots. It does not

establish that an occupation with low platform share has an unrealized commercial

opportunity. A large difference may reflect platform specialization, consumer demand,

the success component of applicability, taxonomy splits or task concentration.



The interactive page includes occupations such as economists and human resources

specialists, plus the exact highest-share task links. A team should inspect these

task-level examples, identify the actual workplace workflow, and record review and

quality requirements before deciding whether to pilot a tool. The rank difference

helps select a question to investigate, rather than answering the personnel decision.



## Why organization changes the answer



The second case is a hypothetical eight-person research team: six analysts and two

reviewers, each with 30 usable hours per week. Briefs require scoping, preparation,

drafting, review, coordination and possible rework. Expected output is bounded by

the smaller of analyst capacity, reviewer capacity and requested cases. Expected

accepted output additionally accounts for residual errors after one rework pass.



At default assumptions, AI reduces preparation from 1.5 to 0.9 hours and drafting

from 2 to 0.8 hours. It also changes review, coordination, training and error costs.

No such changes are estimated from the source indicators. A 98% expected quality

floor excludes alternatives with unacceptable residual error. The model compares

the same 12-week horizon, including training during weeks 1–2 and a six-week

recruitment delay. Existing salary already pays for time spent in training, so the

model subtracts training capacity without adding its wage value to cash cost again.



## Table III. Hypothetical team decision, default assumptions



| Alternative | Expected accepted briefs | Quality, percent | Incremental contribution, USD |

| --- | ---: | ---: | ---: |

| Current workflow | 521.6 | 99.00 | 0 |

| AI without training | 355.4 | 97.50 | −62,941; below quality floor |

| AI + role-specific training | 493.3 | 98.80 | −16,692 |

| AI + training + task reallocation | 665.7 | 98.80 | +43,639 |

| Recruit one analyst | 534.9 | 99.00 | −3,219 |

| AI + training + recruit one reviewer | 596.7 | 98.80 | +8,607 |



Notes: Expected fractional outputs over 12 weeks, nominal hypothetical USD. Value

per accepted brief is USD 350. Contribution equals assumed accepted-output value

minus the listed cash costs; increments compare with the same baseline. The

reallocation alternative moves one existing analyst to review and preserves the

eight-person payroll. It adds 40 hours of role qualification during weeks 1–2 and moves the employee in week 3. It assumes qualification is then feasible, a

substantive feasibility condition requiring a competency assessment. Initial errors

are 10% at baseline, 25% for untrained AI and 12% for trained AI. One rework pass

resolves 90% of initial errors. All other parameters and equations are in

`workflow-assumptions.md`; weekly results are in `workflow-default.json`.



Under these assumptions, training alone produces fewer accepted briefs because

review is the binding constraint after drafting becomes faster. Moving a qualified

employee to review relaxes that constraint. The model's recommended alternative

maximizes contribution among quality-eligible options, without interpreting released

capacity as layoffs. With demand reduced to 30 cases/week, the existing workflow

is preferred: extra capacity has no value at the margin. At demand of 90 and trained

review of 0.8 hours/case, adding a reviewer is preferred. The interface recalculates

the full alternatives when the reader changes demand, quality, value, review time

or recruitment delay. These are conditional comparisons, not forecasts.



## Measurement and reproducibility



Atlas independently reconstructs all 785 published Microsoft applicability scores

from activity-level coverage, completion, impact and original/nonphysical task

weights. The maximum absolute numerical difference is below 1e−10. This verifies

the source equation's implementation, not whether its classifiers measure the

intended workplace construct.



The separate task-text exercise evaluates a keyword baseline and a multinomial

Naive Bayes classifier against Microsoft's published physical/nonphysical labels.

Labels are generated by the source's classifier, so the exercise measures agreement

with silver labels. It provides a held-out split, confusion matrix and pending

human-review queue; it is not an independently human-validated AI-exposure model.

The benchmark JSON gives the exact current sample and metrics.



## Table IV. Task-text measurement against published silver labels



| Classifier | Balanced accuracy | Physical precision | Physical recall | Physical F1 |

| --- | ---: | ---: | ---: | ---: |

| Majority label | 50.0% | 0.0% | 0.0% | 0.0% |

| Fixed physical-action keyword rule | 60.2% | 89.5% | 22.4% | 35.8% |

| Multinomial Naive Bayes | 85.9% | 86.2% | 81.4% | 83.8% |



Notes: Official O*NET 29.0 supplies all 18,796 matched unique task IDs. Identical

normalized wording stays in one split: 15,051 training IDs and 3,745 held-out IDs,

with zero exact-text overlap. Groups are stratified by their majority silver label,

ordered by minimum numeric ID, and every fifth group is held out. The vocabulary

and probabilities are learned from training text only, with no holdout tuning.

Sixteen wording groups have conflicting source labels, illustrating label noise.

The Naive Bayes confusion matrix has 1,304 true positives, 1,935 true negatives,

209 false positives and 297 false negatives. This is a systematic benchmark split,

not a representative sample or a human accuracy estimate. Related wording can

still cross groups. Forty disagreement cases form a pending human-review queue.



`atlas workbench --output my-research` rebuilds the site and a portable SQLite

warehouse offline from bundled licensed aggregates. The warehouse separates

source units, preserves task allocation weights, and includes monthly BLS/FRED

observations. Executable SQL reconstructs the task mass, ranks the occupation gaps

using window functions, and compares industry-series endpoints while displaying

each series' own dates. The Python test suite compares SQL ranks with the analysis

and browser results with the Python organization model. The original wage, skill

and market research and local occupation explorer remain available.



## What a next empirical study would need



A causal claim about training or task redesign requires workplace outcomes and a

credible counterfactual. A prospective study could assign eligible teams to the

existing workflow, tools plus training, and tools plus training plus qualified

review reallocation; measure accepted output, blind quality review and total labor

hours; and account for spillovers at the team level. Power, assignment and the

primary endpoint would need to be specified before collecting outcomes. No such

experiment has been conducted in this project. The current deliverable supplies

measurement diagnostics and a testable organizational mechanism.



## Sources and attribution



[Tomlinson, Jaffe, Wang, Counts and Suri, Working with AI](https://github.com/microsoft/working-with-ai)

(v1.1; CC BY 4.0), [Handa et al., Anthropic Economic Index initial release](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_02_10)

(data CC-BY, version unspecified), [O*NET taxonomies and crosswalks](https://www.onetcenter.org/taxonomy.html),

and [Felten, Raj and Seamans, AIOE](https://github.com/AIOE-Data/AIOE).

O*NET is sponsored by the U.S. Department of Labor, Employment and Training

Administration, and developed by the National Center for O*NET Development.

Atlas modifies these data through normalization, crosswalking, allocation,

ranking and aggregation. See `data-attribution.md` for pinned versions and changes.

