import pandas as pd
import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

SPECIES_EMOJI = {"dog": "🐶", "cat": "🐱", "other": "🐾"}
TIME_EMOJI    = {"morning": "🌅", "afternoon": "☀️", "evening": "🌙"}
FREQ_EMOJI    = {"once": "1️⃣", "daily": "🔁", "weekly": "📅"}

PRIORITY_BADGE = {
    "high":   "🔴 high",
    "medium": "🟡 medium",
    "low":    "🟢 low",
}

# Row background colors keyed by raw priority value
PRIORITY_ROW_COLOR = {
    "high":   "background-color: #b71c1c; color: white",   # deep red
    "medium": "background-color: #e65100; color: white",   # deep orange
    "low":    "background-color: #1b5e20; color: white",   # deep green
}

def fmt_priority(p: str) -> str:
    return PRIORITY_BADGE.get(p, p)

def fmt_time(t: str | None) -> str:
    if not t:
        return "🕐 any"
    return f"{TIME_EMOJI.get(t, '')} {t}"

def fmt_freq(f: str) -> str:
    return f"{FREQ_EMOJI.get(f, '')} {f}"

def _priority_row_style(row: pd.Series) -> list[str]:
    """Return CSS style strings for every cell in a row based on its Priority column."""
    raw = row.get("_priority", "")
    style = PRIORITY_ROW_COLOR.get(raw, "")
    return [style] * len(row)

def styled_task_table(
    tasks: list[Task],
    include_freq: bool = True,
    scheduler=None,
    show_score: bool = False,
) -> "pd.io.formats.style.Styler":
    """Build a colour-coded, styled DataFrame from a list of Task objects."""
    rows = []
    for t in tasks:
        row = {
            "Pet":       t.pet_name or "—",
            "Task":      t.title,
            "⏱ Min":     t.duration_minutes,
            "Priority":  fmt_priority(t.priority),
            "Time slot": fmt_time(t.preferred_time),
            "_priority": t.priority,
        }
        if include_freq:
            row["Frequency"] = fmt_freq(t.frequency)
        if show_score and scheduler is not None:
            row["Score"] = round(scheduler.weighted_score(t), 1)
        rows.append(row)

    df = pd.DataFrame(rows)
    hidden = ["_priority"]
    styler = (
        df.style
        .apply(_priority_row_style, axis=1)
        .hide(axis="index")
        .hide(hidden, axis="columns")
    )
    return styler

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Smart daily care scheduling for your pets.")

# --- Session state ---
if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# Step 1: Owner setup
# ---------------------------------------------------------------------------
st.header("👤 Owner Info")

with st.form("owner_form"):
    owner_name       = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input("Available time today (minutes)", min_value=10, max_value=480, value=90)
    start_time       = st.text_input("Preferred start time", value="08:00")
    submitted        = st.form_submit_button("Save Owner")
    if submitted:
        existing = st.session_state.owner
        if existing is None:
            st.session_state.owner = Owner(
                name=owner_name,
                available_minutes=int(available_minutes),
                preferred_start_time=start_time,
            )
            st.success(f"Owner '{owner_name}' saved!")
        else:
            existing.name              = owner_name
            existing.available_minutes = int(available_minutes)
            existing.preferred_start_time = start_time
            st.success("Owner info updated. Pets and tasks kept.")

if st.session_state.owner is None:
    st.info("Fill in your owner info above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Step 2: Add a Pet
# ---------------------------------------------------------------------------
st.divider()
st.header("🐾 Add a Pet")

with st.form("pet_form"):
    pet_name = st.text_input("Pet name", value="Max")
    species  = st.selectbox("Species", ["dog", "cat", "other"])
    age      = st.number_input("Age", min_value=0, max_value=30, value=3)
    add_pet  = st.form_submit_button("Add Pet")
    if add_pet:
        existing_names = [p.name.lower() for p in owner.pets]
        if pet_name.lower() in existing_names:
            st.warning(f"A pet named '{pet_name}' already exists.")
        else:
            owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
            st.success(f"{SPECIES_EMOJI.get(species, '🐾')} Added {pet_name} the {species}!")

if owner.pets:
    pet_pills = "  ".join(
        f"{SPECIES_EMOJI.get(p.species, '🐾')} **{p.name}** ({p.species}, {p.age}y)"
        for p in owner.pets
    )
    st.markdown(pet_pills)

# ---------------------------------------------------------------------------
# Step 3: Add a Task
# ---------------------------------------------------------------------------
st.divider()
st.header("📋 Add a Task")

if not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        pet_options       = [p.name for p in owner.pets]
        selected_pet_name = st.selectbox("For which pet?", pet_options)
        task_title        = st.text_input("Task title", value="Morning walk")
        duration          = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority          = st.selectbox("Priority", ["high", "medium", "low"])
        preferred_time    = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        frequency         = st.selectbox("Frequency", ["once", "daily", "weekly"])
        add_task          = st.form_submit_button("Add Task")
        if add_task:
            pet = next(p for p in owner.pets if p.name == selected_pet_name)
            pet.add_task(Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                preferred_time=None if preferred_time == "any" else preferred_time,
                frequency=frequency,
            ))
            st.success(
                f"{fmt_freq(frequency)} Added '{task_title}' "
                f"({fmt_priority(priority)}) to {selected_pet_name}'s tasks."
            )

# ---------------------------------------------------------------------------
# Pending task list with filter + sort
# ---------------------------------------------------------------------------
all_pending = owner.get_all_tasks()

if all_pending:
    st.divider()
    st.subheader("📌 Pending Tasks")

    filter_options  = ["All pets"] + [p.name for p in owner.pets]
    selected_filter = st.selectbox("Filter by pet", filter_options, key="filter_pet")

    scheduler_preview = Scheduler(owner)
    filtered = (
        all_pending
        if selected_filter == "All pets"
        else scheduler_preview.filter_tasks(pet_name=selected_filter, completed=False)
    )

    sorted_pending = scheduler_preview.sort_by_time(filtered)

    if sorted_pending:
        st.dataframe(styled_task_table(sorted_pending), use_container_width=True)
    else:
        st.info("No pending tasks for this pet.")

# ---------------------------------------------------------------------------
# Step 4: Generate Schedule
# ---------------------------------------------------------------------------
st.divider()
st.header("🗓️ Generate Today's Schedule")

schedule_mode = st.radio(
    "Scheduling mode",
    ["Priority (high → medium → low)", "Weighted Score (urgency + overdue + efficiency)"],
    horizontal=True,
)

if st.button("Build Schedule", type="primary"):
    if not all_pending:
        st.warning("No pending tasks to schedule. Add some tasks first.")
    else:
        scheduler = Scheduler(owner)
        if "Weighted" in schedule_mode:
            scheduler.build_weighted_plan()
        else:
            scheduler.build_plan()

        # --- Conflict warnings ---
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.subheader("⚠️ Scheduling Conflicts")
            for conflict in conflicts:
                st.warning(conflict)
        else:
            st.success("✅ No scheduling conflicts — your plan looks clean!")

        # --- Time budget metric ---
        total_scheduled = sum(t.duration_minutes for t in scheduler.schedule)
        col1, col2, col3 = st.columns(3)
        col1.metric("Tasks scheduled", len(scheduler.schedule))
        col2.metric("Minutes used", total_scheduled)
        col3.metric("Minutes remaining", owner.available_minutes - total_scheduled)

        # --- Scheduled tasks ---
        st.subheader("Today's Schedule")
        if "Weighted" in schedule_mode:
            st.caption("Ranked by urgency score (priority base + overdue days + efficiency bonus)")
        else:
            st.caption("Sorted by priority (🔴 → 🟡 → 🟢), then by time slot (🌅 → ☀️ → 🌙)")
        if scheduler.schedule:
            sorted_schedule = scheduler.sort_by_time()
            if "Weighted" in schedule_mode:
                st.dataframe(
                    styled_task_table(sorted_schedule, scheduler=scheduler, show_score=True),
                    use_container_width=True,
                )
            else:
                st.dataframe(styled_task_table(sorted_schedule), use_container_width=True)
        else:
            st.warning("No tasks fit in the available time. Try increasing available minutes.")

        # --- Skipped tasks ---
        if scheduler.skipped:
            st.subheader("⏭️ Skipped (didn't fit)")
            st.dataframe(
                styled_task_table(scheduler.skipped, include_freq=False),
                use_container_width=True,
            )

        # --- Full explanation ---
        with st.expander("📝 See full explanation"):
            st.text(scheduler.get_explanation())
