from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from contests.models import Contest, ContestProblem
from contests.similarity import fingerprints, similarity, tokens
from problems.models import Problem
from submissions.models import Submission

User = get_user_model()

ORIGINAL = """
import java.util.*;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        long[] dp = new long[n + 1];
        dp[0] = 1;
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= 3 && j <= i; j++) {
                dp[i] += dp[i - j];
            }
        }
        System.out.println(dp[n] % 1000000007);
    }
}
"""

# The same program with names changed, comments added, reformatted.
DISGUISED = """
import java.util.*;
public class Solution {
  // my own solution :)
  public static void main(String[] args) {
    Scanner input = new Scanner(System.in);
    int count = input.nextInt();
    long[] ways = new long[count + 1]; ways[0] = 1;
    for (int a = 1; a <= count; a++)
    {
      for (int b = 1; b <= 3 && b <= a; b++) { ways[a] += ways[a - b]; }
    }
    System.out.println(ways[count] % 999);   /* print */
  }
}
"""

DIFFERENT = """
import java.util.*;
public class Solution {
    static long ways(int n, Map<Integer, Long> memo) {
        if (n < 0) return 0;
        if (n == 0) return 1;
        if (memo.containsKey(n)) return memo.get(n);
        long total = ways(n - 1, memo) + ways(n - 2, memo) + ways(n - 3, memo);
        memo.put(n, total);
        return total;
    }
    public static void main(String[] args) throws Exception {
        java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(System.in));
        int n = Integer.parseInt(r.readLine().trim());
        System.out.println(ways(n, new HashMap<>()));
    }
}
"""


class FingerprintTests(SimpleTestCase):
    def test_tokens_ignore_names_literals_and_comments(self):
        self.assertEqual(tokens("int x = 5; // hi"), ["int", "I", "=", "L", ";"])
        self.assertEqual(tokens('String s = "a // not a comment";'), ["I", "I", "=", "L", ";"])

    def test_renamed_copy_scores_high_and_different_code_low(self):
        original = fingerprints(ORIGINAL)
        self.assertGreater(similarity(original, fingerprints(DISGUISED)), 0.8)
        self.assertLess(similarity(original, fingerprints(DIFFERENT)), 0.5)


class SimilarityApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.ADMIN
        )
        problem = Problem.objects.create(title="Stairs", slug="stairs", statement="x", is_published=True)
        now = timezone.now()
        self.contest = Contest.objects.create(
            title="Quiz", start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1)
        )
        ContestProblem.objects.create(contest=self.contest, problem=problem, letter="A")
        for name, source in (("alice", ORIGINAL), ("bob", DISGUISED), ("carol", DIFFERENT)):
            user = User.objects.create_user(username=name, password="pass12345")
            Submission.objects.create(
                user=user, problem=problem, contest=self.contest, source_code=source,
                status=Submission.Status.ACCEPTED,
            )

    def _get(self, user, query=""):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.get(f"/api/contests/{self.contest.id}/similarity/{query}")

    def test_flags_only_the_copied_pair(self):
        resp = self._get(self.admin)
        self.assertEqual(resp.status_code, 200, resp.content)
        pairs = resp.data["pairs"]
        self.assertEqual(
            [{p["a"]["username"], p["b"]["username"]} for p in pairs], [{"alice", "bob"}]
        )
        self.assertEqual(pairs[0]["problem_letter"], "A")

    def test_threshold_validation_and_permissions(self):
        self.assertEqual(self._get(self.admin, "?threshold=abc").status_code, 400)
        self.assertEqual(self._get(self.admin, "?threshold=0.1").status_code, 400)
        student = User.objects.get(username="alice")
        self.assertEqual(self._get(student).status_code, 403)
