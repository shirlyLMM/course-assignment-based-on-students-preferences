import csv
import random

NUM_STUDENTS = 300
NUM_COURSES = 10
COURSES = [f"Course_{i}" for i in range(1, NUM_COURSES + 1)]


def rank_to_ordered(rank_row):
    """
    将 {course: rank} 字典转换为按偏好顺序排列的课程列表。
    rank=1 表示最喜欢，排在最前面。
    """
    return [course for course, _ in sorted(rank_row.items(), key=lambda x: x[1])]


def generate_random_preferences():
    """每个学生对 10 门课程完全随机排序"""
    rows = []
    for student_id in range(1, NUM_STUDENTS + 1):
        ordered = COURSES[:]
        random.shuffle(ordered)
        row = {
            "student_id": student_id,
            "name": f"Student_{student_id:03d}",
        }
        for i, course in enumerate(ordered, start=1):
            row[f"pref_{i}"] = course
        rows.append(row)
    return rows


def generate_biased_preferences():
    """
    大多数学生偏好 Course_1 和 Course_2：
    - Course_1 或 Course_2 排在第 1 位，另一门排第 2 位
    - 约 20% 的学生将 Course_1/2 中一门排第 1，另一门随机插入第 2-4 名
    - 约 10% 的学生完全随机
    """
    rows = []
    for student_id in range(1, NUM_STUDENTS + 1):
        r = random.random()
        if r < 0.70:
            # 偏好型：Course_1/2 占据前两名
            top_two = random.sample(["Course_1", "Course_2"], 2)
            remaining = [c for c in COURSES if c not in top_two]
            random.shuffle(remaining)
            ordered = top_two + remaining
        elif r < 0.90:
            # 部分偏好：Course_1/2 中一门排第 1，另一门随机插入第 2-4 名
            top_course = random.choice(["Course_1", "Course_2"])
            second_fav = "Course_2" if top_course == "Course_1" else "Course_1"
            remaining = [c for c in COURSES if c not in [top_course, second_fav]]
            random.shuffle(remaining)
            insert_pos = random.randint(1, 3)
            remaining.insert(insert_pos, second_fav)
            ordered = [top_course] + remaining
        else:
            # 无偏好：完全随机
            ordered = COURSES[:]
            random.shuffle(ordered)

        row = {
            "student_id": student_id,
            "name": f"Student_{student_id:03d}",
        }
        for i, course in enumerate(ordered, start=1):
            row[f"pref_{i}"] = course
        rows.append(row)
    return rows


def write_csv(filename, rows):
    fieldnames = ["student_id", "name"] + [f"pref_{i}" for i in range(1, NUM_COURSES + 1)]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"已生成：{filename}（{len(rows)} 条记录）")


def write_sessions_csv(filename, capacity=30):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["session_name", "capacity"])
        writer.writeheader()
        for course in COURSES:
            writer.writerow({"session_name": course, "capacity": capacity})
    print(f"已生成：{filename}（{len(COURSES)} 门课程，每门容量 {capacity}）")


if __name__ == "__main__":
    random.seed(42)

    random_rows = generate_random_preferences()
    write_csv("students_random.csv", random_rows)

    biased_rows = generate_biased_preferences()
    write_csv("students_biased.csv", biased_rows)

    write_sessions_csv("sessions.csv", capacity=30)

    # 简单验证：打印偏向数据中各课程被排第 1 的学生数量
    print("\n[偏向数据] 各课程被排在第 1 志愿的学生数：")
    for course in COURSES:
        count = sum(1 for r in biased_rows if r["pref_1"] == course)
        print(f"  {course}: {count} 人")
