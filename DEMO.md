# Demo walkthrough — Judge Engine

## 1. Seed the demo (one command)

With Docker running:

```powershell
docker compose exec backend python manage.py seed_demo
```

To wipe and recreate demo problems/contest:

```powershell
docker compose exec backend python manage.py seed_demo --reset
```

## 2. Accounts

| Who | Username | Password | Use for |
|-----|----------|----------|---------|
| Teacher | `admin` | `JudgeDev-Admin-ChangeMe!` | Django Admin, create content |
| Student | `alice` | `demo123` | Main walkthrough |
| Student | `bob` | `demo123` | Second browser / scoreboard |
| Student | `carol` | `demo123` | Optional third solver |

> Change the admin password after first login. `seed_demo` only sets student passwords on create (use `--reset-passwords` to force).

## 3. 10-minute script

### A. Teacher view (2 min)
1. Open http://localhost:8000/admin/ — log in as `admin`
2. Show **Problems** (3 published) and **Contests → Demo Cup 2026**
3. Open http://localhost:3000 — log in as `admin`, click **Django Admin** link in the nav

### B. Student solves practice (3 min)
1. Log out → log in as `alice`
2. **Problems** → **A Plus B**
3. Paste this Java and **Submit**:

```java
import java.util.*;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        System.out.println(sc.nextInt() + sc.nextInt());
    }
}
```

4. Wait for **Accepted** (polls every ~1.5s)

### C. Live contest + scoreboard (5 min)
1. Still as `alice`: **Contests** → **Demo Cup 2026** (already registered)
2. Open problem **A**, submit the same solution (contest-scoped)
3. In another browser/incognito, log in as `bob`, open the contest, submit **Maximum of Two**:

```java
import java.util.*;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int a = sc.nextInt(), b = sc.nextInt();
        System.out.println(Math.max(a, b));
    }
}
```

4. Open **Scoreboard** — show ranks updating; highlight current user row
5. Optional: submit a wrong answer as `carol` to show penalty / WA cells

### D. Wrong-answer beat (optional, 1 min)
As `alice` on **Sum 1 to N**, submit a buggy solution:

```java
public class Solution {
    public static void main(String[] args) {
        System.out.println(0);
    }
}
```

Expect **WrongAnswer**, then fix with the loop/`n*(n+1)/2` formula and get **Accepted**.

## 4. Talking points
- Hidden tests never leave the API (only samples shown)
- Untrusted Java runs in a Docker sandbox (no network, memory/CPU caps)
- Contests use ICPC-style scoring (solves, then penalty time)
- Teachers manage roster/problems in Django Admin — no public signup
