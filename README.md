# PawPal+ (Module 2 Project)

> A smart pet-care scheduling app built with Python and Streamlit.

## Features

**Smart Scheduling**
- **Priority-based planning** — tasks are ranked high → medium → low and packed into the day until `available_minutes` runs out; anything that doesn't fit is surfaced in a "Skipped" list so nothing is forgotten
- **Chronological sorting** — `sort_by_time()` orders any task list by time slot (morning → afternoon → evening) using a lookup-table key, so the daily plan always reads the way a real day flows
- **Per-pet filtering** — `filter_tasks(pet_name, completed)` lets the UI show only the tasks belonging to a chosen pet, with optional completion filtering
- **Weighted urgency scoring** *(Challenge 1 — advanced algorithm)* — `weighted_score(task)` computes a numeric score for each task from three additive components:
  - *Priority base*: high = 100, medium = 50, low = 10
  - *Overdue bonus*: +5 per day past `due_date`, capped at +50 — tasks that are late rise automatically
  - *Efficiency bonus*: +15 when the task uses ≤ 25 % of available time, rewarding quick wins

  `build_weighted_plan()` ranks by this score (descending) instead of the raw priority bucket, so an overdue medium task can outrank an on-time high task, and a 5-minute grooming task beats a lower-scoring but time-consuming one. The UI exposes this as a **Weighted Score** mode toggle alongside the standard Priority mode.

**How Agent Mode was used to implement weighted scoring**

Claude Code's Agent Mode was prompted to design and implement the algorithm end-to-end:

1. *Design prompt* — "Design a numeric urgency scoring function for a pet-care task scheduler. The score should account for priority tier, how many days overdue the task is, and whether the task is a quick win relative to available time. Return the formula and Python implementation."
2. *Review prompt* — "Review `weighted_score()` and `build_weighted_plan()` in `pawpal_system.py`. Are there edge cases (no due_date, zero available_minutes) that could cause errors? Suggest fixes."
3. *UI integration prompt* — "Add a radio toggle to the Streamlit schedule section so the user can switch between priority-based and weighted-score scheduling without losing their task data."

Agent Mode compressed what would have been several design-and-debug cycles into a single guided session, surfacing the `division-by-zero` guard on `available_minutes` and the `min(..., 50)` cap on the overdue bonus before they could become runtime bugs.

**Conflict Detection**
- **Same-pet slot clash** — warns when one pet has two tasks assigned to the same time slot
- **Cross-pet high-priority clash** — warns when multiple pets have high-priority tasks competing in the same slot
- **Slot overload** — warns when tasks in a single slot total more than 60 minutes
- All warnings are displayed as `st.warning` banners before the schedule so the owner can fix conflicts before their day starts

**Recurring Tasks**
- Tasks can be set to `"once"`, `"daily"`, or `"weekly"` frequency at creation time
- Marking a daily task complete automatically schedules the next occurrence for tomorrow (`timedelta(days=1)`)
- Marking a weekly task complete schedules the next occurrence in 7 days (`timedelta(weeks=1)`)
- One-off tasks are simply marked done with no follow-up

**Professional UI**
- Owner, pet, and task data persist across Streamlit reruns via `st.session_state`
- Pending tasks are filtered by pet and sorted chronologically before the plan is built
- Clean table display with only user-relevant columns (internal flags hidden)
- Full plain-English explanation of scheduling decisions available via expandable section

---

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

---

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

The `Scheduler` class includes four algorithmic improvements beyond the basic daily plan:

- **`sort_by_time()`** — orders any task list by time slot (morning → afternoon → evening) using a lambda key, so the daily plan reads in chronological order regardless of how tasks were added.
- **`filter_tasks(pet_name, completed)`** — filters across all pets by owner name and/or completion status, making it easy to view only what still needs to be done for a specific pet.
- **`detect_conflicts()`** — scans pending tasks and returns plain-English warning messages for three situations: the same pet having multiple tasks in one slot, high-priority tasks competing across different pets in the same slot, and any slot whose total duration exceeds 60 minutes. It never crashes the app — it always returns a list (empty means no conflicts).
- **Recurring tasks (`frequency` + `mark_task_complete()`)** — tasks can be marked `"daily"` or `"weekly"`. When completed, `Scheduler.mark_task_complete()` automatically adds the next occurrence to the pet's task list with a new `due_date` calculated using Python's `timedelta` (today + 1 day for daily, today + 7 days for weekly).

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Testing PawPal+

### Run the tests

```bash
python3 -m pytest tests/test_pawpal.py -v
```

### What the tests cover

**Sorting correctness**
- Tasks added in any order are returned morning → afternoon → evening
- Tasks with no `preferred_time` always sort to the end
- An empty schedule returns `[]` without raising an error

**Recurrence logic**
- Marking a daily task complete spawns a new task due tomorrow (`today + 1 day`)
- Marking a weekly task complete spawns a new task due in 7 days
- One-off tasks (`frequency="once"`) produce no next occurrence
- A brand-new pet with no tasks has an empty pending list

**Conflict detection**
- Two tasks for the same pet in the same time slot produce a conflict warning
- Tasks in different slots for the same pet produce no conflict
- High-priority tasks across two different pets in the same slot produce a cross-pet warning
- A slot whose total duration exceeds 60 minutes produces an overload warning

**Weighted scoring (Challenge 1)**
- Priority base is correct for each tier (high=100, medium=50, low=10)
- Overdue tasks score higher than identical on-time tasks
- Overdue bonus is capped at 50 regardless of days late
- Quick tasks (≤ 25% of available time) earn the +15 efficiency bonus
- Tasks with no `due_date` receive zero overdue bonus
- An overdue medium task is scheduled before an on-time high task when scores demand it
- Tasks that exceed remaining time go to `skipped`, not `schedule`

### Confidence Level

★★★★★ (5 / 5)

- All 20 tests pass across every major behavior
- Covers happy paths, edge cases, and the full weighted scoring algorithm
- Both scheduling modes (`build_plan` and `build_weighted_plan`) are tested end-to-end
