"""
Tests for PawPal+ core logic.
Run with: python -m pytest
"""

from datetime import date, timedelta

from pawpal_system import Task, Pet, Owner, Scheduler


def test_mark_complete_changes_status():
    """Calling mark_complete() should set is_complete to True."""
    task = Task(title="Morning walk", duration_minutes=30, priority="high")
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Max", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_sort_by_time_chronological_order():
    """sort_by_time() returns tasks in morning → afternoon → evening order."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = Pet(name="Luna", species="cat", age=2)
    owner.add_pet(pet)

    evening_task = Task(title="Play", duration_minutes=15, priority="low", preferred_time="evening")
    morning_task = Task(title="Feed", duration_minutes=10, priority="high", preferred_time="morning")
    afternoon_task = Task(title="Groom", duration_minutes=20, priority="medium", preferred_time="afternoon")

    pet.add_task(evening_task)
    pet.add_task(morning_task)
    pet.add_task(afternoon_task)

    scheduler = Scheduler(owner)
    scheduler.build_plan()
    sorted_tasks = scheduler.sort_by_time()

    times = [t.preferred_time for t in sorted_tasks]
    assert times == ["morning", "afternoon", "evening"]


def test_sort_by_time_unset_preferred_time_goes_last():
    """Tasks with no preferred_time should appear after all named slots."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=4)
    owner.add_pet(pet)

    no_time = Task(title="Vet call", duration_minutes=10, priority="low", preferred_time=None)
    morning_task = Task(title="Walk", duration_minutes=30, priority="high", preferred_time="morning")

    pet.add_task(no_time)
    pet.add_task(morning_task)

    scheduler = Scheduler(owner)
    scheduler.build_plan()
    sorted_tasks = scheduler.sort_by_time()

    assert sorted_tasks[0].preferred_time == "morning"
    assert sorted_tasks[-1].preferred_time is None


def test_sort_by_time_on_pet_with_no_tasks():
    """sort_by_time() on an empty schedule should return an empty list without error."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Empty", species="other", age=1)
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    scheduler.build_plan()
    assert scheduler.sort_by_time() == []


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_daily_task_spawns_next_occurrence_after_completion():
    """Marking a daily task complete adds a new task due tomorrow."""
    pet = Pet(name="Buddy", species="dog", age=5)
    daily = Task(title="Morning walk", duration_minutes=30, priority="high", frequency="daily")
    pet.add_task(daily)

    next_task = pet.mark_task_complete("Morning walk")

    # Original task is now complete
    assert pet.tasks[0].is_complete is True
    # A new task was created
    assert next_task is not None
    assert next_task.title == "Morning walk"
    assert next_task.frequency == "daily"
    assert next_task.is_complete is False
    assert next_task.due_date == date.today() + timedelta(days=1)


def test_weekly_task_spawns_occurrence_seven_days_out():
    """Marking a weekly task complete sets due_date to today + 7 days."""
    pet = Pet(name="Whiskers", species="cat", age=3)
    weekly = Task(title="Flea treatment", duration_minutes=15, priority="medium", frequency="weekly")
    pet.add_task(weekly)

    next_task = pet.mark_task_complete("Flea treatment")

    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(weeks=1)


def test_once_task_does_not_spawn_next_occurrence():
    """A one-off task should return None from next_occurrence()."""
    task = Task(title="Vet visit", duration_minutes=60, priority="high", frequency="once")
    assert task.next_occurrence() is None


def test_pet_with_no_tasks_has_no_pending():
    """A brand-new pet should have an empty pending-task list."""
    pet = Pet(name="Ghost", species="other", age=0)
    assert pet.get_pending_tasks() == []


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_detect_conflicts_same_pet_same_slot():
    """Two tasks for the same pet in the same slot should produce a conflict warning."""
    owner = Owner(name="Sam", available_minutes=120)
    pet = Pet(name="Daisy", species="dog", age=2)
    owner.add_pet(pet)

    pet.add_task(Task(title="Walk", duration_minutes=20, priority="high", preferred_time="morning"))
    pet.add_task(Task(title="Feed", duration_minutes=10, priority="high", preferred_time="morning"))

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) >= 1
    assert any("Daisy" in c and "morning" in c for c in conflicts)


def test_detect_conflicts_no_conflict_different_slots():
    """Tasks in different time slots for the same pet should not conflict."""
    owner = Owner(name="Sam", available_minutes=120)
    pet = Pet(name="Daisy", species="dog", age=2)
    owner.add_pet(pet)

    pet.add_task(Task(title="Walk", duration_minutes=20, priority="high", preferred_time="morning"))
    pet.add_task(Task(title="Feed", duration_minutes=10, priority="high", preferred_time="evening"))

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()

    # No same-pet/same-slot conflict expected
    assert not any("Daisy" in c and "Conflict" in c for c in conflicts)


def test_detect_conflicts_cross_pet_high_priority_same_slot():
    """Two high-priority tasks from different pets in the same slot should warn."""
    owner = Owner(name="Sam", available_minutes=120)
    pet1 = Pet(name="Rex", species="dog", age=3)
    pet2 = Pet(name="Luna", species="cat", age=2)
    owner.add_pet(pet1)
    owner.add_pet(pet2)

    pet1.add_task(Task(title="Walk", duration_minutes=20, priority="high", preferred_time="morning"))
    pet2.add_task(Task(title="Feed", duration_minutes=10, priority="high", preferred_time="morning"))

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()

    assert any("high-priority" in c and "morning" in c for c in conflicts)


def test_detect_conflicts_slot_overload():
    """Tasks totalling more than 60 minutes in one slot should trigger an overload warning."""
    owner = Owner(name="Sam", available_minutes=200)
    pet = Pet(name="Bear", species="dog", age=4)
    owner.add_pet(pet)

    for i in range(4):
        pet.add_task(Task(title=f"Task{i}", duration_minutes=20, priority="low", preferred_time="afternoon"))

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()

    assert any("overloaded" in c and "afternoon" in c for c in conflicts)


# ---------------------------------------------------------------------------
# Weighted scoring (Challenge 1 algorithm)
# ---------------------------------------------------------------------------

def _make_scheduler(available_minutes: int = 120) -> tuple[Owner, Pet, Scheduler]:
    owner = Owner(name="Alex", available_minutes=available_minutes)
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)
    return owner, pet, Scheduler(owner)


def test_weighted_score_priority_base():
    """Score for a non-overdue task with no efficiency bonus equals the priority base."""
    owner, pet, scheduler = _make_scheduler(available_minutes=100)
    # duration = 50 min → 50/100 = 50% > 25%, so no efficiency bonus
    task = Task(title="Vet", duration_minutes=50, priority="high", due_date=date.today())
    pet.add_task(task)
    assert scheduler.weighted_score(task) == 100.0


def test_weighted_score_overdue_bonus():
    """An overdue task scores higher than an identical on-time task."""
    owner, pet, scheduler = _make_scheduler(available_minutes=200)
    on_time = Task(title="Walk", duration_minutes=60, priority="medium", due_date=date.today())
    overdue = Task(title="Bath", duration_minutes=60, priority="medium",
                   due_date=date.today() - timedelta(days=3))
    pet.add_task(on_time)
    pet.add_task(overdue)
    assert scheduler.weighted_score(overdue) > scheduler.weighted_score(on_time)


def test_weighted_score_overdue_bonus_capped_at_50():
    """Overdue bonus is capped at 50 regardless of how many days late."""
    owner, pet, scheduler = _make_scheduler(available_minutes=500)
    very_overdue = Task(
        title="Groom", duration_minutes=200, priority="low",
        due_date=date.today() - timedelta(days=100),
    )
    pet.add_task(very_overdue)
    # base=10, overdue capped at 50, no efficiency bonus (200/500=40%>25%)
    assert scheduler.weighted_score(very_overdue) == 60.0


def test_weighted_score_efficiency_bonus():
    """A quick task (≤ 25% of available time) earns the +15 efficiency bonus."""
    owner, pet, scheduler = _make_scheduler(available_minutes=100)
    quick = Task(title="Feed", duration_minutes=25, priority="low")   # 25/100 = 25% → bonus
    slow  = Task(title="Walk", duration_minutes=26, priority="low")   # 26/100 = 26% → no bonus
    pet.add_task(quick)
    pet.add_task(slow)
    assert scheduler.weighted_score(quick) == scheduler.weighted_score(slow) + 15


def test_weighted_score_no_due_date_gives_zero_overdue():
    """Tasks without a due_date should not receive any overdue bonus."""
    owner, pet, scheduler = _make_scheduler(available_minutes=200)
    task = Task(title="Play", duration_minutes=60, priority="medium", due_date=None)
    pet.add_task(task)
    # base=50, no overdue, no efficiency bonus (60/200=30%>25%)
    assert scheduler.weighted_score(task) == 50.0


def test_build_weighted_plan_overdue_outranks_higher_priority():
    """An overdue medium task should be scheduled before an on-time high task when scores demand it."""
    owner, pet, scheduler = _make_scheduler(available_minutes=40)
    # Overdue medium: base 50 + overdue 50 (cap) = 100
    overdue_medium = Task(
        title="Overdue groom", duration_minutes=20, priority="medium",
        due_date=date.today() - timedelta(days=20),
    )
    # On-time high, slow: base 100, no overdue, no efficiency bonus (20/40=50%)
    high_on_time = Task(title="On-time walk", duration_minutes=20, priority="high")

    pet.add_task(overdue_medium)
    pet.add_task(high_on_time)

    scheduler.build_weighted_plan()
    # Both fit in 40 min; the overdue medium should appear first (higher score)
    assert scheduler.schedule[0].title == "Overdue groom"


def test_build_weighted_plan_skips_tasks_that_dont_fit():
    """Tasks that exceed remaining available time go to skipped, not schedule."""
    owner, pet, scheduler = _make_scheduler(available_minutes=20)
    pet.add_task(Task(title="Short", duration_minutes=20, priority="high"))
    pet.add_task(Task(title="Long",  duration_minutes=30, priority="low"))

    scheduler.build_weighted_plan()

    scheduled_titles = [t.title for t in scheduler.schedule]
    skipped_titles   = [t.title for t in scheduler.skipped]
    assert "Short" in scheduled_titles
    assert "Long"  in skipped_titles
