# 课程分配系统

## 概述

本项目模拟了 **300 名学生**对 **10 门课程**的完整偏好排序，并使用**随机化串行独裁算法（Randomized Serial Dictatorship）**将每位学生分配到一门课程，目标是最小化全体学生的总"失望分"。

---

## 文件列表

| 文件 | 说明 |
|------|------|
| `generate_preferences.py` | 生成模拟偏好数据和课程容量文件 |
| `assign.py` | 课程分配算法主程序 |
| `students_random.csv` | 输入：300 名学生，偏好完全随机 |
| `students_biased.csv` | 输入：300 名学生，偏好集中于 Course_1 和 Course_2 |
| `sessions.csv` | 输入：10 门课程，每门容量 30 |
| `assignment_random.csv` | 输出：随机场景的最优分配结果 |
| `assignment_biased.csv` | 输出：集中偏好场景的最优分配结果 |
| `report_random.txt` | 输出：随机场景的分配报告 |
| `report_biased.txt` | 输出：集中偏好场景的分配报告 |

---

## 输入文件格式

### `students_random.csv` / `students_biased.csv`

每行代表一名学生，列为：

| 字段 | 类型 | 说明 |
|------|------|------|
| `student_id` | 整数 | 学生编号，1 ~ 300 |
| `name` | 字符串 | 学生姓名占位符（如 `Student_001`） |
| `pref_1` | 字符串 | 第 1 志愿课程名称 |
| `pref_2` | 字符串 | 第 2 志愿课程名称 |
| ... | ... | ... |
| `pref_10` | 字符串 | 第 10 志愿课程名称 |

示例行：

```
student_id,name,pref_1,pref_2,...,pref_10
1,Student_001,Course_3,Course_1,...,Course_5
```

### `sessions.csv`

| 字段 | 说明 |
|------|------|
| `session_name` | 课程名称 |
| `capacity` | 最大容量（本项目均为 30） |

---

## 两个偏好场景

### `students_random.csv` — 随机偏好

- 每位学生的志愿顺序完全随机
- 每门课被列为第 1 志愿的学生数大致相等（约 30 人/课）
- 适合作为**无偏好基准场景**

### `students_biased.csv` — 集中偏好

- 约 **94%** 的学生将 Course_1 或 Course_2 列为第 1 志愿
  - Course_1：约 140 人列为第 1 志愿
  - Course_2：约 142 人列为第 1 志愿
- 适合模拟**热门课程竞争场景**，测试算法在资源争抢下的表现

---

## 算法说明

`assign.py` 实现随机化串行独裁算法：

1. 随机打乱学生顺序
2. 按顺序让每位学生获得其志愿列表中第一个还有空位的课程
3. 重复多次试验，记录总失望分最低的前 N 个方案
4. 若连续 P 次无改善则提前停止

**计分规则**：获得第 k 志愿 = k 分；未能分配 = (课程数 + 1) 分。总分越低越好。

---

## 运行方法

### 第一步：生成数据

```bash
python generate_preferences.py
```

生成 `students_random.csv`、`students_biased.csv`、`sessions.csv`。

### 第二步：运行分配算法

随机偏好场景：

```bash
python assign.py --students students_random.csv \
                 --out-assignment assignment_random.csv \
                 --out-report report_random.txt
```

集中偏好场景：

```bash
python assign.py --students students_biased.csv \
                 --out-assignment assignment_biased.csv \
                 --out-report report_biased.txt
```

### 可配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--students` | `students_random.csv` | 学生偏好输入文件 |
| `--sessions` | `sessions.csv` | 课程容量输入文件 |
| `--seed` | `42` | 随机种子（保证可复现） |
| `--trials` | `100` | 最大试验次数 |
| `--top` | `5` | 保留最优方案数量 |
| `--patience` | `20` | 早停耐心值（连续无改善次数） |
| `--out-assignment` | `assignment.csv` | 分配结果输出文件 |
| `--out-report` | `report.txt` | 报告输出文件 |

---

## 输出文件格式

### `assignment_*.csv`

| 字段 | 说明 |
|------|------|
| `student_id` | 学生编号 |
| `name` | 学生姓名 |
| `assigned_session` | 分配到的课程（未分配则为 `UNASSIGNED`） |
| `preference_rank` | 该课程在该学生志愿中的排名 |

### `report_*.txt`

包含：总失望分、未分配人数、各志愿命中人数分布、各课程座位使用情况、前 N 个最优方案的得分。

---

## 样本输出结果

| 场景 | 最优总分 | 试验次数 | 获得第 1 志愿人数 |
|------|----------|----------|------------------|
| 随机偏好 | 349 | 31 | 270 / 300 |
| 集中偏好 | 699 | 22 | 76 / 300 |

集中偏好场景中，由于 Course_1 和 Course_2 竞争激烈（各仅 30 个座位，却有约 280 人将其列为第 1 志愿），大量学生最终获得第 3 志愿（142 人）。
