# Research-team workflow: model contract

This is a hypothetical personnel and task-allocation case. No organization supplied
the parameters. The model does not estimate an AI treatment effect.

The decision is how an eight-person research team can meet demand while keeping
expected quality at or above 98%. Six analysts prepare briefs and two reviewers
check the evidence and conclusions. A brief requires both roles in sequence.
Labor is fixed within each week, work can be divided continuously, and there is
no inventory carried between weeks. These simplifications exclude queueing and
indivisible deadlines; the capacity bound can overstate achievable throughput.

## Fixed assumptions

| Quantity | Assumption |
| --- | ---: |
| Horizon | 12 weeks by default; CLI accepts 2–104 |
| Existing analysts / reviewers | 6 / 2 |
| Usable hours per person per week | 30 / 30 |
| Existing payroll | USD 8,200/week |
| Scope a brief | 0.5 analyst hours |
| Prepare evidence | 1.5 analyst hours; 0.9 with AI |
| Draft | 2 analyst hours; 0.8 with AI |
| Rework, conditional on an initial error | 1 analyst hour + 0.5 reviewer hours |
| Baseline review / coordination | 1.2 / 0.05 reviewer hours per case |
| Untrained AI review / coordination | 1.6 / 0.25 reviewer hours per case |
| Trained AI coordination | 0.15 reviewer hours per case |
| Baseline / untrained AI initial error rate | 10% / 25% |
| Rework resolution probability | 90% after one pass |
| Training | 12 h per analyst, 8 h per reviewer, split across weeks 1–2 |
| Extra role qualification for task reallocation | 40 analyst hours over the qualification delay; two weeks by default |
| Direct training expense | USD 2,000 per trained alternative |
| AI tool expense | USD 400/week |
| Recruitment expense | USD 2,500, paid in week 1 |
| Additional analyst / reviewer salary | USD 900 / 1,400 per week after recruitment delay |

The browser controls weekly demand, value per accepted brief, trained AI review
time, trained initial error rate and recruitment delay. Defaults are 60 briefs,
USD 350, 1.2 hours, 12% and six weeks. JSON exports retain the complete current
parameter set and weekly trajectory. Currency values are hypothetical nominal USD,
without an empirically calibrated price year or discounting.

## Equations

Let e be the initial error probability and q = 1 − 0.1e the expected final quality
after one rework pass. Every completed case incurs expected rework hours, including
cases that ultimately retain an error. This quality specification is a modeling
assumption, with no independent measurement of error detection or severity.

Analyst hours/case = scope + preparation + drafting + e × 1.
Reviewer hours/case = review + coordination + e × 0.5.

For week t, each role's capacity is its nonnegative usable hours after training,
divided by its hours/case. Completed cases = min(analyst capacity, reviewer
capacity, weekly demand). Expected accepted cases = completed cases × q.
Demand is the number of requested cases before residual quality rejection.
Outputs can be fractional because the model calculates expectations.

Contribution = sum(expected accepted cases) × assumed value per accepted case −
sum(listed cash costs). The recommendation maximizes contribution among alternatives
with q ≥ 0.98. Incremental contribution and cash cost compare every alternative
with the same baseline. Training time reduces capacity; existing salaries already
pay for this time, so its wage value is not added again to cash costs.

## Alternatives and feasibility

1. Current workflow retains the existing team and methods.
2. AI without training changes preparation, drafting, review and error assumptions.
3. AI with training adds time and direct expense while reducing assumed errors.
4. Task reallocation moves one existing analyst to review after the qualification delay
   (two weeks by default). An extra 40 analyst hours are spent on role qualification
   during that delay, beyond the AI training. The employee stays in analysis until
   the delay ends, then becomes the third reviewer.
   It preserves eight people and their existing payroll. This assumes the person
   can qualify for the reviewer role after those 40 hours; real implementation requires
   a competency assessment and may require a pay adjustment or longer training.
5. Recruit one analyst without AI. Recruitment expense is paid even if the hire
   arrives after the horizon; salary begins in the week after the delay ends.
6. AI, training and one additional reviewer use the same recruitment timing.
   New hires are assumed prequalified and do not consume the initial staff's training time.

The baseline is feasible at the quality floor for all allowed inputs. Low demand
can make new capacity worthless. A high trained error rate can make every AI
alternative ineligible. Faster trained review can favor an extra reviewer at high
demand. No alternative implies automatic layoffs, and no parameter is inferred
from AIOE, Microsoft or Anthropic occupation indicators.

## Validation and interpretation

The Python and browser implementations are checked on multiple parameter sets,
including low demand, slow review, the exact quality threshold, a recruitment delay
longer than the horizon and training that exhausts usable hours. These checks
verify calculation, not the realism of parameters. Validate hours, errors, demand,
reviewer qualification and value in the intended organization before using the
model for a personnel decision.
