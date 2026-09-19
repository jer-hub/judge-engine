export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "student" | "admin";
  school_id: string;
  class_section: string;
  is_platform_admin: boolean;
};

export type ProblemListItem = {
  id: number;
  title: string;
  slug: string;
  difficulty: string;
  tags: string[];
  time_limit_ms: number;
  memory_limit_mb: number;
  is_published: boolean;
  test_case_count?: number;
  run_all_tests?: boolean;
  created_by_username?: string | null;
  created_at?: string;
};

export type SampleTest = {
  id: number;
  order: number;
  input_data: string;
  expected_output: string;
  points: number;
};

export type ProblemDetail = ProblemListItem & {
  statement: string;
  run_all_tests: boolean;
  sample_tests: SampleTest[];
};

export type Submission = {
  id: number;
  problem: number;
  problem_slug: string;
  problem_title?: string;
  contest: number | null;
  username: string;
  language: string;
  status: string;
  compile_error: string;
  submitted_at: string;
  judged_at: string | null;
  source_code?: string;
  results: Array<{
    id: number;
    test_case_order: number;
    is_sample: boolean;
    verdict: string;
    execution_time_ms: number | null;
    memory_used_kb: number | null;
  }>;
};

export type ContestListItem = {
  id: number;
  title: string;
  start_time: string;
  end_time: string;
  is_public: boolean;
  status: "upcoming" | "active" | "past";
  freeze_scoreboard_minutes_before_end: number;
  problem_count?: number;
};

export type ContestDetail = ContestListItem & {
  description: string;
  is_frozen: boolean;
  is_registered: boolean;
  server_time: string;
  problems: Array<{
    id: number;
    letter: string;
    display_order: number;
    points: number;
    problem: ProblemListItem;
  }>;
  participants?: Array<{
    id: number;
    user_id: number;
    username: string;
    registered_at: string;
  }>;
};

export type AdminUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "student" | "admin";
  school_id: string;
  class_section: string;
  is_active: boolean;
  is_platform_admin: boolean;
  date_joined?: string;
};

export type UserImportError = {
  row: number;
  username: string;
  error: string;
};

export type UserImportResult = {
  created: number;
  skipped: number;
  failed: number;
  dry_run: boolean;
  created_usernames: string[];
  errors: UserImportError[];
};

export type Scoreboard = {
  contest_id: number;
  title: string;
  is_frozen: boolean;
  freeze_at: string | null;
  server_time: string;
  problems: Array<{
    letter: string;
    problem_id: number;
    slug: string;
    title: string;
  }>;
  standings: Array<{
    rank: number;
    username: string;
    solved: number;
    penalty: number;
    problems: Array<{
      letter: string;
      problem_id: number;
      solved: boolean;
      attempts: number;
      solve_time_min: number | null;
      pending: boolean;
    }>;
  }>;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type RunPreview = {
  status: string;
  compile_error: string;
  stdout: string;
  stderr: string;
  execution_time_ms: number | null;
};
