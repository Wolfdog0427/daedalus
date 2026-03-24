def levenshtein(a: str, b: str) -> int:
    """Very small, efficient Levenshtein distance."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 2:
        return 99  # too different

    # Initialize DP table correctly
    dp = [[j for j in range(len(b) + 1)]]
    dp += [[i] + [0] * len(b) for i in range(1, len(a) + 1)]

    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[-1][-1]


COMMANDS = [
    "show goals",
    "list goals",
    "switch goal",
    "cancel goal",
    "clear goals",
]


def fuzzy_match(text: str):
    """
    Conservative fuzzy matching:
    - Only corrects very close typos (distance <= 2)
    - Never guesses between multiple candidates
    - Returns None if not confident
    """
    text = text.strip().lower()

    best = None
    best_dist = 99

    for cmd in COMMANDS:
        dist = levenshtein(text, cmd)
        if dist < best_dist:
            best = cmd
            best_dist = dist

    if best_dist <= 2:
        return best

    return None
