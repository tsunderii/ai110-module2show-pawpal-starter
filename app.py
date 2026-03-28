import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Session state: create Owner once, persist across reruns ---
if "owner" not in st.session_state:
    st.session_state.owner = None

# --- Step 1: Owner setup ---
st.header("Owner Info")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input("Available time today (minutes)", min_value=10, max_value=480, value=90)
    start_time = st.text_input("Preferred start time", value="08:00")
    submitted = st.form_submit_button("Save Owner")
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
            existing.name = owner_name
            existing.available_minutes = int(available_minutes)
            existing.preferred_start_time = start_time
            st.success("Owner info updated. Pets and tasks kept.")

if st.session_state.owner is None:
    st.info("Fill in your owner info above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# --- Step 2: Add a Pet ---
st.divider()
st.header("Add a Pet")

with st.form("pet_form"):
    pet_name = st.text_input("Pet name", value="Max")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    age = st.number_input("Age", min_value=0, max_value=30, value=3)
    add_pet = st.form_submit_button("Add Pet")
    if add_pet:
        existing_names = [p.name.lower() for p in owner.pets]
        if pet_name.lower() in existing_names:
            st.warning(f"A pet named '{pet_name}' already exists.")
        else:
            owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
            st.success(f"Added {pet_name} the {species}!")

if owner.pets:
    st.write("**Your pets:**", ", ".join(p.name for p in owner.pets))

# --- Step 3: Add a Task ---
st.divider()
st.header("Add a Task")

if not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        pet_options = [p.name for p in owner.pets]
        selected_pet_name = st.selectbox("For which pet?", pet_options)
        task_title = st.text_input("Task title", value="Morning walk")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", ["high", "medium", "low"])
        preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])
        frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
        add_task = st.form_submit_button("Add Task")
        if add_task:
            pet = next(p for p in owner.pets if p.name == selected_pet_name)
            pet.add_task(Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                preferred_time=None if preferred_time == "any" else preferred_time,
                frequency=frequency,
            ))
            st.success(f"Added '{task_title}' ({frequency}) to {selected_pet_name}'s tasks.")

# --- Pending task list with optional pet filter ---
all_pending = owner.get_all_tasks()
if all_pending:
    st.divider()
    st.subheader("Pending Tasks")

    # Filter control
    filter_options = ["All pets"] + [p.name for p in owner.pets]
    selected_filter = st.selectbox("Filter by pet", filter_options, key="filter_pet")

    scheduler_preview = Scheduler(owner)
    if selected_filter == "All pets":
        filtered = all_pending
    else:
        filtered = scheduler_preview.filter_tasks(pet_name=selected_filter, completed=False)

    # Display sorted by preferred time
    sorted_pending = scheduler_preview.sort_by_time(filtered)

    display_rows = [
        {
            "Pet": t.pet_name or "—",
            "Task": t.title,
            "Duration (min)": t.duration_minutes,
            "Priority": t.priority,
            "Time slot": t.preferred_time or "any",
            "Frequency": t.frequency,
        }
        for t in sorted_pending
    ]
    st.table(display_rows)

# --- Step 4: Generate Schedule ---
st.divider()
st.header("Generate Today's Schedule")

if st.button("Build Schedule"):
    if not all_pending:
        st.warning("No pending tasks to schedule. Add some tasks first.")
    else:
        scheduler = Scheduler(owner)
        scheduler.build_plan()

        # --- Conflict warnings shown first ---
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.subheader("Scheduling Conflicts Detected")
            for conflict in conflicts:
                st.warning(conflict)
        else:
            st.success("No scheduling conflicts — your plan looks clean!")

        # --- Scheduled tasks sorted chronologically ---
        st.subheader("Today's Schedule")
        if scheduler.schedule:
            sorted_schedule = scheduler.sort_by_time()
            schedule_rows = [
                {
                    "Pet": t.pet_name or "—",
                    "Task": t.title,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Time slot": t.preferred_time or "any",
                    "Frequency": t.frequency,
                }
                for t in sorted_schedule
            ]
            st.table(schedule_rows)
            total = sum(t.duration_minutes for t in scheduler.schedule)
            st.success(f"Total: {total} min used of {owner.available_minutes} min available")
        else:
            st.warning("No tasks fit in the available time. Try increasing available minutes.")

        # --- Skipped tasks ---
        if scheduler.skipped:
            st.subheader("Skipped (didn't fit in available time)")
            skipped_rows = [
                {
                    "Pet": t.pet_name or "—",
                    "Task": t.title,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Time slot": t.preferred_time or "any",
                }
                for t in scheduler.skipped
            ]
            st.table(skipped_rows)

        # --- Plain-English explanation ---
        with st.expander("See full explanation"):
            st.text(scheduler.get_explanation())
