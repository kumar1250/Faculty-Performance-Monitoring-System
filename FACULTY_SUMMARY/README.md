# FACULTY_SUMMARY App

A read-only Django app that **aggregates all module data for any faculty member**
and exposes two kinds of endpoints:

1. **Module details** — all 16 modules with count / approved / pending / rejected / points  
2. **Total points** — sum of approved points across every module

---

## Setup

### 1. Add to `INSTALLED_APPS` in `settings.py`

```python
INSTALLED_APPS = [
    ...
    'FACULTY_SUMMARY',
]
```

### 2. Register the URL in `Faculty_Performance_Monitoring_System/urls.py`

```python
path('summary/', include('FACULTY_SUMMARY.urls')),
```

> No migrations needed — this app has **no models** of its own.

---

## API Reference

All endpoints require `Authorization: Bearer <token>` header.

### Own summary (any authenticated user)

```
GET /summary/faculty-summary/my-summary/
```

**Response**
```json
{
  "user_id": 5,
  "register_no": "22BCS001",
  "username": "Dr. Ravi Kumar",
  "email": "ravi@mvgr.ac.in",
  "role": "faculty",
  "modules": [
    {
      "module": "Book Publications",
      "total": 3,
      "approved": 2,
      "pending": 1,
      "rejected": 0,
      "points": 17.5
    },
    { "module": "Certificate Courses Done", ... },
    ...
  ],
  "total_points": 84.5
}
```

---

### Module details by user_id (HOD / Principal / Dean)

```
GET /summary/faculty-summary/by-user/?user_id=5
```

Same response shape as `my-summary`.

---

### Module details by register_no (HOD / Principal / Dean)

```
GET /summary/faculty-summary/by-register/?register_no=22BCS001
```

Same response shape as `my-summary`.

---

### Own total points only (any authenticated user)

```
GET /summary/faculty-summary/total-points/
```

**Response**
```json
{
  "user_id": 5,
  "register_no": "22BCS001",
  "username": "Dr. Ravi Kumar",
  "total_points": 84.5
}
```

---

### Total points for a specific user_id (HOD / Principal / Dean)

```
GET /summary/faculty-summary/total-points-by-user/?user_id=5
```

Same response shape as `total-points`.

---

### All faculty list with total points (HOD / Principal / Dean)

```
GET /summary/faculty-summary/all-faculty/
GET /summary/faculty-summary/all-faculty/?role=faculty   ← default
GET /summary/faculty-summary/all-faculty/?role=hod
```

**Response**
```json
{
  "count": 42,
  "faculty": [
    {
      "user_id": 5,
      "register_no": "22BCS001",
      "username": "Dr. Ravi Kumar",
      "email": "ravi@mvgr.ac.in",
      "total_points": 84.5
    },
    ...
  ]
}
```

---

## Modules Covered

| # | Module |
|---|--------|
| 1 | Book Publications |
| 2 | Certificate Courses Done |
| 3 | Conference Publications |
| 4 | Consultancy |
| 5 | FDPs Attended |
| 6 | FDPs Organized |
| 7 | Funded Projects |
| 8 | Journal Publications |
| 9 | Learning Material |
| 10 | Memberships with Professional Bodies |
| 11 | Patents |
| 12 | Research Guidance |
| 13 | Sessions & Delivering Talks/Lectures |
| 14 | Student Counselling / Mentoring |
| 15 | Student Project Works |
| 16 | Theory Courses Handled |
