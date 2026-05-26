"""
assign.py — Randomized Serial Dictatorship course assignment algorithm.

Algorithm overview
------------------
Serial Dictatorship: students are processed one by one in some order.
Each student is assigned the highest-ranked session that still has a
free seat. The order in which students are processed determines who
gets their top choices, so a random shuffle is used to avoid bias.

Randomized version: repeat the shuffle-and-assign process many times
(trials). Keep track of the best few assignments found (lowest total
disappointment score). Stop early if no improvement is seen for a
configurable number of consecutive trials, or if the theoretical
minimum score is reached.

Scoring (disappointment score)
-------------------------------
  - Getting 1st choice  → 1 point
  - Getting 2nd choice  → 2 points
  - ...
  - Getting k-th choice → k points
  - Unassigned          → (number of sessions + 1) points  [penalty]
Lower total score = happier group overall.

Usage
-----
    python assign.py [--students students_random.csv] [--sessions sessions.csv]
                     [--seed 42] [--trials 100] [--top 5] [--patience 20]
                     [--out-assignment assignment.csv] [--out-report report.txt]
"""

import csv       # reading/writing CSV files
import random    # shuffling student order
import argparse  # command-line argument parsing
from collections import defaultdict  # convenient counter dicts


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_students(path):
    """
    Read the students CSV and return a list of student records.

    Each record is a dict:
        {
            "student_id": str,   # e.g. "1"
            "name":       str,   # e.g. "Student_001"
            "prefs":      list,  # ["Course_3", "Course_1", ...] — index 0 is top choice
        }

    The CSV is expected to have columns: student_id, name, pref_1, pref_2, ..., pref_N.
    The number of preference columns is detected automatically.
    """
    students = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Collect pref_1, pref_2, ... in order until a column is missing
            prefs = []
            i = 1
            while f"pref_{i}" in row:
                prefs.append(row[f"pref_{i}"])
                i += 1
            students.append({
                "student_id": row["student_id"],
                "name":       row["name"],
                "prefs":      prefs,
            })
    return students


def load_sessions(path):
    """
    Read the sessions CSV and return a capacity dict.

    Returns: { session_name: capacity }  e.g. {"Course_1": 30, "Course_2": 30, ...}

    The CSV is expected to have columns: session_name, capacity.
    """
    sessions = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sessions[row["session_name"]] = int(row["capacity"])
    return sessions


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def compute_cost(assignment, students, num_sessions):
    """
    Calculate the total disappointment score for a given assignment.

    Parameters
    ----------
    assignment   : dict  { student_id -> {"session": str|None, "rank": int|None} }
                   Output of run_trial(). "rank" is 1-based (1 = top choice).
    students     : list  The full student list (used to catch any student missing
                   from the assignment dict, which should not happen in practice).
    num_sessions : int   Number of available sessions. Used to compute the penalty
                   for unassigned students: penalty = num_sessions + 1.

    Returns
    -------
    int  Total cost. Lower is better.
         Example: 300 students all getting 1st choice → cost = 300.
    """
    # An unassigned student costs more than any valid assignment rank,
    # making the algorithm strongly prefer placing everyone somewhere.
    penalty = num_sessions + 1

    total = 0
    for s in students:
        sid = s["student_id"]
        if sid in assignment and assignment[sid]["session"] is not None:
            # Add the rank this student received (1 = best, num_sessions = worst)
            total += assignment[sid]["rank"]
        else:
            # Student could not be placed in any session → apply penalty
            total += penalty
    return total


def run_trial(students, session_capacities, rng):
    """
    Run one Serial Dictatorship trial with a randomly shuffled student order.

    How it works
    ------------
    1. Shuffle the student list randomly (using the shared rng for reproducibility).
    2. Process students one by one in that shuffled order.
    3. Each student gets the first session in their preference list that still
       has a free seat. Once a seat is taken it is unavailable to later students.
    4. If a student's entire preference list is exhausted with no free seat,
       they are marked as UNASSIGNED.

    Why random order matters
    ------------------------
    The student processed first has the best chance of getting their top choice.
    By randomising the order each trial, we avoid systematically favouring any
    particular student and explore many different assignment outcomes.

    Parameters
    ----------
    students           : list   Full student list from load_students().
    session_capacities : dict   { session_name: total_capacity } — NOT modified in place;
                                a local copy is made so the original is preserved.
    rng                : random.Random   Seeded RNG instance shared across all trials,
                                ensuring the sequence of shuffles is reproducible.

    Returns
    -------
    dict  { student_id -> {"session": str|None, "rank": int|None} }
          "rank" is 1-based. None values mean the student was unassigned.
    """
    # Copy capacities so we can decrement seats without affecting other trials
    seats = dict(session_capacities)

    # Build an index list and shuffle it — we shuffle indices rather than the
    # student list itself to avoid mutating the original list.
    order = list(range(len(students)))
    rng.shuffle(order)

    assignment = {}
    for idx in order:
        s = students[idx]
        sid = s["student_id"]
        assigned = False
        # Walk through this student's preferences from most to least preferred
        for rank, session in enumerate(s["prefs"], start=1):
            if seats.get(session, 0) > 0:
                # Found a session with a free seat — assign and stop searching
                seats[session] -= 1
                assignment[sid] = {"session": session, "rank": rank}
                assigned = True
                break
        if not assigned:
            # All preferred sessions are full; student cannot be placed
            assignment[sid] = {"session": None, "rank": None}
    return assignment


def run_all_trials(students, session_capacities, seed, num_trials, top_n, patience):
    """
    Run multiple Serial Dictatorship trials and track the best assignments found.

    Strategy
    --------
    Each trial uses a different random student order (controlled by the shared rng).
    Because the same rng is used sequentially across all trials, the full sequence
    of shuffles is determined by the initial seed, making results reproducible.

    Early stopping conditions (whichever comes first):
      1. Theoretical minimum reached: every student got their 1st choice
         (cost == number of students). No further improvement is possible.
      2. Patience exhausted: no improvement for `patience` consecutive trials.
         This avoids wasting time when the search has likely converged.

    Parameters
    ----------
    students           : list   Student records from load_students().
    session_capacities : dict   { session_name: capacity } from load_sessions().
    seed               : int    Random seed. Passed to random.Random() so the RNG
                                is isolated from any other random state in the program.
    num_trials         : int    Maximum number of trials to run.
    top_n              : int    Number of best assignments to keep. Keeping more than
                                one lets you inspect near-optimal alternatives.
    patience           : int    Stop after this many consecutive trials with no
                                improvement to the best cost seen so far.

    Returns
    -------
    tuple (top_assignments, trials_run)
      top_assignments : list of (assignment_dict, cost), sorted ascending by cost,
                        length <= top_n. Index 0 is the best assignment found.
      trials_run      : int  Actual number of trials completed (may be < num_trials
                        if early stopping triggered).
    """
    rng = random.Random(seed)  # Isolated RNG — seed controls the full sequence of shuffles
    num_sessions = len(session_capacities)
    theoretical_min = len(students)  # Best possible score: every student gets rank 1

    top_assignments = []   # Maintained as a sorted list; trimmed to top_n after each trial
    no_improve_count = 0   # Counts consecutive trials without a new best cost
    best_cost = float("inf")  # Tracks the lowest cost seen so far across all trials

    for trial in range(num_trials):
        assignment = run_trial(students, session_capacities, rng)
        cost = compute_cost(assignment, students, num_sessions)

        # Update top-N list
        top_assignments.append((assignment, cost))
        top_assignments.sort(key=lambda x: x[1])
        if len(top_assignments) > top_n:
            top_assignments = top_assignments[:top_n]
        # Sort ascending so index 0 is always the best

        # Early stopping logic
        if cost < best_cost:
            best_cost = cost
            no_improve_count = 0  # Reset counter — we found a new best
        else:
            no_improve_count += 1

        if best_cost == theoretical_min:
            return top_assignments, trial + 1

        if no_improve_count >= patience:
            return top_assignments, trial + 1

    # All trials completed without early stopping
    return top_assignments, num_trials


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_assignment_csv(path, best_assignment, students):
    """
    Write the best assignment to a CSV file.

    Output columns
    --------------
    student_id       : original student ID from the input file
    name             : student name
    assigned_session : session name, or "UNASSIGNED" if the student could not be placed
    preference_rank  : the rank (1-based) of the assigned session in the student's
                       preference list, or "N/A" if unassigned

    Parameters
    ----------
    path            : str   Output file path.
    best_assignment : dict  { student_id -> {"session": str|None, "rank": int|None} }
    students        : list  Used to preserve the original row order in the output.
    """
    # Build a lookup for student names
    name_lookup = {s["student_id"]: s["name"] for s in students}
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["student_id", "name", "assigned_session", "preference_rank"])
        writer.writeheader()
        for s in students:
            sid = s["student_id"]
            info = best_assignment.get(sid, {"session": None, "rank": None})
            writer.writerow({
                "student_id": sid,
                "name": name_lookup[sid],
                "assigned_session": info["session"] if info["session"] else "UNASSIGNED",
                "preference_rank": info["rank"] if info["rank"] else "N/A",
            })


def write_report(path, top_assignments, students, session_capacities, num_trials_run):
    """
    Write a human-readable summary report to a text file.

    The report includes:
      - Run parameters (student count, session count, trials run)
      - Best total cost and number of unassigned students
      - Preference rank distribution: how many students got rank 1, 2, 3, ...
      - Session utilisation: seats filled vs. capacity for each session
      - Top-N assignment costs found across all trials

    Parameters
    ----------
    path               : str   Output file path.
    top_assignments    : list  From run_all_trials(). Index 0 is the best.
    students           : list  Full student list.
    session_capacities : dict  { session_name: capacity }
    num_trials_run     : int   Actual number of trials completed.
    """
    best_assignment, best_cost = top_assignments[0]
    num_sessions = len(session_capacities)
    num_students = len(students)

    # Tally rank distribution for best assignment
    rank_counts = defaultdict(int)
    unassigned = 0
    for s in students:
        sid = s["student_id"]
        info = best_assignment.get(sid, {"session": None, "rank": None})
        if info["session"] is None:
            unassigned += 1
        else:
            rank_counts[info["rank"]] += 1

    # Session utilisation for best assignment
    session_fill = defaultdict(int)
    for info in best_assignment.values():
        if info["session"]:
            session_fill[info["session"]] += 1

    lines = []
    lines.append("=" * 60)
    lines.append("COURSE ASSIGNMENT REPORT")
    lines.append("=" * 60)
    lines.append(f"Students          : {num_students}")
    lines.append(f"Sessions          : {num_sessions}")
    lines.append(f"Trials run        : {num_trials_run}")
    lines.append(f"Best total cost   : {best_cost}")
    lines.append(f"Unassigned        : {unassigned}")
    lines.append("")
    lines.append("--- Preference rank distribution (best assignment) ---")
    for rank in range(1, num_sessions + 1):
        count = rank_counts.get(rank, 0)
        lines.append(f"  Rank {rank:2d}: {count:4d} students")
    lines.append("")
    lines.append("--- Session utilisation (best assignment) ---")
    for session, capacity in sorted(session_capacities.items()):
        filled = session_fill.get(session, 0)
        lines.append(f"  {session:<12}: {filled:3d} / {capacity}")
    lines.append("")
    lines.append("--- Top assignments found ---")
    for i, (_, cost) in enumerate(top_assignments, start=1):
        lines.append(f"  #{i}: total cost = {cost}")
    lines.append("=" * 60)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# Parse command-line arguments. All parameters have sensible defaults so the
# program can be run with no arguments against the default input files.
def parse_args():
    p = argparse.ArgumentParser(description="Course assignment via randomized serial dictatorship")
    p.add_argument("--students",        default="students_biased.csv")
    p.add_argument("--sessions",        default="sessions.csv")
    p.add_argument("--seed",            type=int, default=42)
    p.add_argument("--trials",          type=int, default=100)
    p.add_argument("--top",             type=int, default=5)
    p.add_argument("--patience",        type=int, default=20)
    p.add_argument("--out-assignment",  default="assignment.csv")
    p.add_argument("--out-report",      default="report.txt")
    return p.parse_args()


# Orchestrate the full pipeline: load inputs → run trials → write outputs.
def main():
    args = parse_args()
    students = load_students(args.students)
    session_capacities = load_sessions(args.sessions)
    top_assignments, trials_run = run_all_trials(
        students, session_capacities,
        seed=args.seed, num_trials=args.trials,
        top_n=args.top, patience=args.patience,
    )
    best_assignment, best_cost = top_assignments[0]
    write_assignment_csv(args.out_assignment, best_assignment, students)
    write_report(args.out_report, top_assignments, students, session_capacities, trials_run)
    print(f"Done. Best cost: {best_cost}  |  Trials run: {trials_run}")
    print(f"Results written to {args.out_assignment} and {args.out_report}")


if __name__ == "__main__":
    main()
