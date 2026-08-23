import pandas as pd
from scipy.stats import wilcoxon
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint

EVAL_CSV = "results/evaluation_2026-07-19_19-15-14_full.csv"
SURVEY_CSV = "results/Form_Responses_-_Form_Responses_1.csv"

eval_df = pd.read_csv(EVAL_CSV)
survey_df = pd.read_csv(SURVEY_CSV)

# McNemar's test: rule-based vs Claude, same 100 transactions per dataset
print("McNemar's Test")
for ds in eval_df["dataset"].unique():
    sub = eval_df[eval_df["dataset"] == ds]
    both_correct = (sub["rule_correct"] & sub["claude_correct"]).sum()
    both_wrong = (~sub["rule_correct"] & ~sub["claude_correct"]).sum()
    rule_only = (sub["rule_correct"] & ~sub["claude_correct"]).sum()
    claude_only = (~sub["rule_correct"] & sub["claude_correct"]).sum()
    table = [[both_correct, rule_only], [claude_only, both_wrong]]
    n_disc = rule_only + claude_only
    result = mcnemar(table, exact=n_disc < 25, correction=n_disc >= 25)
    print(f"  {ds}: stat={result.statistic:.4f}, p={result.pvalue:.6f}")

# Wilson 95% confidence intervals on each accuracy figure
print("\nWilson Confidence Intervals")
for ds in eval_df["dataset"].unique():
    sub = eval_df[eval_df["dataset"] == ds]
    n = len(sub)
    for system, col in [("Rule-Based", "rule_correct"), ("Claude", "claude_correct")]:
        k = int(sub[col].sum())
        lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
        print(f"  {ds} | {system}: {k}/{n} (CI: {lo*100:.1f}%-{hi*100:.1f}%)")

# Wilcoxon signed-rank test: paired survey ratings
print("\nWilcoxon Signed-Rank Test")
raw_ease = "Looking at the raw transaction data above, how easy was it to identify the total revenue and total expenses for this month?"
ai_ease = "Looking at the AI Bookkeeping Tool dashboard above, how easy was it to identify the total revenue and total expenses for this month?"
before_conf = "Before seeing anything now, how confident are you in your ability to understand business finances?"
after_dash = "After looking at the product's dashboard, how confident are you now in understanding this business's finances?"
after_plain = "After seeing the plain-English output, how confident would you feel making a financial decision based on it?"

def compare(col_a, col_b, label):
    stat, p = wilcoxon(survey_df[col_a], survey_df[col_b])
    print(f"  {label}: stat={stat:.1f}, p={p:.6f}")

compare(raw_ease, ai_ease, "Raw data vs AI dashboard ease")
compare(before_conf, after_dash, "Confidence before vs after dashboard")
compare(after_dash, after_plain, "Confidence after dashboard vs after plain-English")