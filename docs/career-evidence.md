# Career evidence: labor economics, organization and AI

AI Labor Atlas 0.6.1 · Haojian Dui

The professional claim supported by this portfolio is the ability to turn an
economic question into a source-aware analytical product and a conditional
organizational decision. Source data and classifiers belong to their authors;
this portfolio's work is the harmonization, comparison, implementation, model and
communication. The organization case is hypothetical and has no client outcomes.
Development used AI assistance; the author should review and personally explain
each substantive decision before presenting this as evidence of independent skill.

## Evidence by capability

| Hiring question | Reviewable evidence | What to demonstrate orally |
| --- | --- | --- |
| Can you formulate a labor-market measurement question? | `research-brief.md`, Tables I–II | Why potential ability exposure, consumer task applicability and conversation share are different objects |
| Can you handle difficult joins without hiding missingness? | `comparison.py`, exact task links, acquisition manifest | Why legacy code truncation is wrong, why child counts cannot multiply conversation mass, and why `none` stays in the denominator |
| Can you write meaningful SQL? | `research-queries.sql`, `research.sqlite`, `sql-results.json` | Foreign keys, one-to-many fractional allocation, tied average ranks with windows, source-native monthly endpoints |
| Can you evaluate a text measure? | Table IV, benchmark JSON and pending review queue | Grouped holdout, train-only vocabulary, class imbalance, precision/recall and silver-label limitations |
| Do you understand personnel and organizational economics? | `workflow-assumptions.md` and interactive alternatives | Complementary roles, shadow value of scarce review hours, training opportunity cost, recruitment delay and demand constraints |
| Can you implement reliable analytical tools? | Python/browser agreement checks and installed-package CI | Show one changed assumption, the resulting constraint, and an exported reproducible result |
| Can you communicate to a nontechnical decision maker? | Browser-ready case and research brief | Explain the question, one finding, one consequential assumption and the resulting decision in three minutes |

## Three presentation lengths

**Thirty seconds.** “I study how AI task evidence can inform labor and organization
decisions. I harmonized public occupation indicators and found that only 100 of
190 top-quartile occupations overlap between two platform-based measures. I then
built a transparent team model showing how faster drafting can shift the bottleneck
to review, making task allocation part of the training decision.”

**Three minutes.** Open the live case. Explain the units and common sample, select
Economists or Human Resources Specialists, and inspect its task examples. Show
the organization case: training alone leaves review constrained under the default
assumptions; reallocating a qualified employee changes output. Reduce demand to
30 cases/week and show that the existing workflow becomes the model choice. State
that these personnel results are hypothetical, then export the parameterized result.

**Fifteen minutes.** Walk through the official crosswalk composition and mass
conservation query. Compare the full sample with the positive-use and single-target
sensitivities. Explain the score reconstruction and grouped text holdout. Inspect
one false positive from the review queue. Derive the workflow capacity equation,
discuss the cross-training feasibility assumption, and outline the outcomes and
counterfactual a real workplace evaluation would need.

## Interview questions to prepare

**Why not average the three indicators?** Their constructs and units differ; an
average would silently assign welfare and predictive weights without validation.
Separate evidence can guide a pilot while preserving the reason for disagreement.

**Does a higher conversation share mean more adoption?** It describes a platform's
released conversations. User selection, task mapping, non-work use and many-to-many
occupation links prevent a direct worker-adoption interpretation.

**Why fractionally allocate a shared task?** It conserves source mass and avoids
rewarding occupations with many child codes. Equal weights are a transparent
assumption, so the single-target sensitivity removes that allocation choice at the
cost of dropping information. Neither method reveals actual worker occupations.

**What did the text classifier validate?** A simple model's held-out agreement
with source-generated physical-task labels. It did not validate human judgments,
AI exposure, wage effects or the task model's productivity parameters. A human
adjudication queue is provided and remains pending.

**Why can training lower output?** Drafting savings increase the demand for review
while training uses available time. If review hours bind, analytical capacity has
little immediate marginal value. The model explicitly counts this complementarity.

**Why might the reallocation recommendation fail?** The moved employee may not be
able to qualify quickly, review may require scarce domain expertise, wage adjustments
may be needed, deadlines can be indivisible, or demand/value may be overstated.
These are reasons to measure the workplace parameters, not to infer them from an
occupation-level AI indicator.

**What is still missing for a research economist application?** This project has
no causally identified workplace treatment effect, no independent human annotation
study and no original employer microdata. It is evidence of applied measurement,
analytical engineering and economic reasoning. Applicants should pair it with a
research writing sample and personally defend the code and methods. Academic
credentials and job eligibility are separate from this project.

## Suggested portfolio bullets

- Built a reproducible AI-task research workbench linking 758 SOC occupations across
  public platform indicators; implemented official taxonomy crosswalks, conserved
  99.52% of released task conversation share and reported ranking sensitivity.
- Developed a Python/SQL analytical pipeline and offline interactive case, including
  grouped held-out task-text evaluation and numerical reconstruction of 785 published
  applicability scores; distinguished silver-label agreement from human validation.
- Modeled six training, task-allocation and recruitment alternatives for a hypothetical
  team, incorporating review bottlenecks, error rework, quality constraints and hiring
  delays; exposed assumptions and decision reversals through an exportable interface.

These bullets describe project deliverables, not measured commercial impact.
Use them only after verifying that they accurately represent the author's own
reviewed work and ability to reproduce it.
