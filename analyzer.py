import numpy as np
import pandas as pd
from scipy import stats


class MediationAnalyzer:
    def __init__(self, data, bootstrap_n=5000):
        self.data = data
        self.bootstrap_n = bootstrap_n
        self.results = {}

    def ols(self, y, x_cols):
        # 验证列名
        missing = [c for c in [y] + list(x_cols) if c not in self.data.columns]
        if missing:
            return None

        Y = self.data[y].values
        X = self.data[x_cols].values
        n = len(Y)
        X = np.column_stack([np.ones(n), X])
        k = X.shape[1] - 1

        try:
            beta = np.linalg.lstsq(X, Y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return None

        Y_hat = X @ beta
        resid = Y - Y_hat
        df_res = n - k - 1
        if df_res <= 0:
            return None

        ss_res = resid @ resid
        ss_tot = ((Y - Y.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        r2_adj = 1 - (1 - r2) * (n - 1) / df_res

        ms_reg = (ss_tot - ss_res) / k if k > 0 else 0
        ms_res = ss_res / df_res
        f_stat = ms_reg / ms_res if ms_res > 0 else 0
        f_p = 1 - stats.f.cdf(f_stat, k, df_res)

        try:
            cov = ms_res * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.abs(np.diag(cov)))
        except np.linalg.LinAlgError:
            se = np.zeros(len(beta))

        # 防止除零
        se = np.where(se < 1e-15, 1e-15, se)
        t_vals = beta / se
        p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df_res))

        names = ['截距'] + list(x_cols)
        coef = []
        for i, name in enumerate(names):
            coef.append({
                'var': name, 'beta': beta[i], 'se': se[i],
                't': t_vals[i], 'p': p_vals[i],
                'sig': self._sig(p_vals[i])
            })

        return {
            'y': y, 'x': list(x_cols), 'coef': coef,
            'r2': r2, 'r2_adj': r2_adj,
            'f': f_stat, 'f_p': f_p, 'n': n, 'df': df_res
        }

    @staticmethod
    def _sig(p):
        if p < 0.001: return '***'
        if p < 0.01:  return '**'
        if p < 0.05:  return '*'
        if p < 0.1:   return '.'
        return ''

    def _coef(self, result, idx):
        return result['coef'][idx]['beta'] if result else np.nan

    def _se(self, result, idx):
        return result['coef'][idx]['se'] if result else np.nan

    def simple_mediation(self, x, m, y):
        a_res = self.ols(m, [x])
        a = self._coef(a_res, 1)

        bm_res = self.ols(y, [x, m])
        b = self._coef(bm_res, 2)
        c_prime = self._coef(bm_res, 1)

        c_res = self.ols(y, [x])
        c = self._coef(c_res, 1)

        ab = a * b
        ci_lo, ci_hi = self._boot_simple(x, m, y)
        sobel_z, sobel_p = self._sobel(a_res, bm_res)
        ratio = ab / c if abs(c) > 1e-10 else 0

        self.results = {
            'type': 'simple',
            'x': x, 'm': m, 'y': y,
            'paths': {
                'a (X→M)': a, 'b (M→Y)': b,
                'c (总效应)': c, "c' (直接效应)": c_prime,
                'ab (间接效应)': ab,
            },
            'ci': {'lo': ci_lo, 'hi': ci_hi, 'n': self.bootstrap_n},
            'sobel': {'z': sobel_z, 'p': sobel_p},
            'ratio': ratio,
        }
        return self.results

    def serial_mediation(self, x, m1, m2, y):
        a1_res = self.ols(m1, [x])
        a1 = self._coef(a1_res, 1)

        a2_d21_res = self.ols(m2, [x, m1])
        a2 = self._coef(a2_d21_res, 1)
        d21 = self._coef(a2_d21_res, 2)

        b_res = self.ols(y, [x, m1, m2])
        b1 = self._coef(b_res, 2)
        b2 = self._coef(b_res, 3)
        c_prime = self._coef(b_res, 1)

        c_res = self.ols(y, [x])
        c = self._coef(c_res, 1)

        ind1 = a1 * b1
        ind2 = a2 * b2
        ind3 = a1 * d21 * b2

        ci = self._boot_serial(x, m1, m2, y)

        self.results = {
            'type': 'serial',
            'x': x, 'm1': m1, 'm2': m2, 'y': y,
            'paths': {
                'a1 (X→M1)': a1, 'a2 (X→M2)': a2,
                'b1 (M1→Y)': b1, 'b2 (M2→Y)': b2,
                'd21 (M1→M2)': d21,
                'c (总效应)': c, "c' (直接效应)": c_prime,
            },
            'indirect': {
                'ind1 (X→M1→Y)': ind1, 'ind2 (X→M2→Y)': ind2,
                'ind3 (X→M1→M2→Y)': ind3, 'total': ind1 + ind2 + ind3,
            },
            'ci': ci,
        }
        return self.results

    def _boot_simple(self, x, m, y):
        effects = []
        for _ in range(self.bootstrap_n):
            s = self.data.sample(n=len(self.data), replace=True)
            a_r = self._ols_on(s, m, [x])
            b_r = self._ols_on(s, y, [x, m])
            if a_r and b_r:
                effects.append(self._coef(a_r, 1) * self._coef(b_r, 2))
        if not effects:
            return 0, 0
        return np.percentile(effects, 2.5), np.percentile(effects, 97.5)

    def _boot_serial(self, x, m1, m2, y):
        e1, e2, e3 = [], [], []
        for _ in range(self.bootstrap_n):
            s = self.data.sample(n=len(self.data), replace=True)
            r1 = self._ols_on(s, m1, [x])
            r2 = self._ols_on(s, m2, [x, m1])
            r3 = self._ols_on(s, y, [x, m1, m2])
            if r1 and r2 and r3:
                a1 = self._coef(r1, 1)
                a2 = self._coef(r2, 1)
                d21 = self._coef(r2, 2)
                b1 = self._coef(r3, 2)
                b2 = self._coef(r3, 3)
                e1.append(a1 * b1)
                e2.append(a2 * b2)
                e3.append(a1 * d21 * b2)

        def ci(arr):
            if not arr:
                return (0, 0)
            return (np.percentile(arr, 2.5), np.percentile(arr, 97.5))

        return {'ind1': ci(e1), 'ind2': ci(e2), 'ind3': ci(e3), 'n': self.bootstrap_n}

    def _ols_on(self, data, y, x_cols):
        # 直接在指定数据上计算，不修改self.data
        Y = data[y].values
        X = data[x_cols].values
        n = len(Y)
        X = np.column_stack([np.ones(n), X])
        k = X.shape[1] - 1

        try:
            beta = np.linalg.lstsq(X, Y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return None

        Y_hat = X @ beta
        resid = Y - Y_hat
        df_res = n - k - 1
        if df_res <= 0:
            return None

        ss_res = resid @ resid
        ss_tot = ((Y - Y.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        r2_adj = 1 - (1 - r2) * (n - 1) / df_res

        ms_reg = (ss_tot - ss_res) / k if k > 0 else 0
        ms_res = ss_res / df_res
        f_stat = ms_reg / ms_res if ms_res > 0 else 0
        f_p = 1 - stats.f.cdf(f_stat, k, df_res)

        try:
            cov = ms_res * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.abs(np.diag(cov)))
        except np.linalg.LinAlgError:
            se = np.zeros(len(beta))

        se = np.where(se < 1e-15, 1e-15, se)
        t_vals = beta / se
        p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df_res))

        names = ['截距'] + list(x_cols)
        coef = []
        for i, name in enumerate(names):
            coef.append({
                'var': name, 'beta': beta[i], 'se': se[i],
                't': t_vals[i], 'p': p_vals[i],
                'sig': self._sig(p_vals[i])
            })

        return {
            'y': y, 'x': list(x_cols), 'coef': coef,
            'r2': r2, 'r2_adj': r2_adj,
            'f': f_stat, 'f_p': f_p, 'n': n, 'df': df_res
        }

    def _sobel(self, a_res, b_res):
        if not a_res or not b_res:
            return 0, 1
        a = self._coef(a_res, 1)
        a_se = self._se(a_res, 1)
        b_idx = len(b_res['x'])
        b = self._coef(b_res, b_idx)
        b_se = self._se(b_res, b_idx)

        se_ab = np.sqrt(b**2 * a_se**2 + a**2 * b_se**2)
        if se_ab < 1e-15:
            return 0, 1
        z = a * b / se_ab
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        return z, p

    def summary(self):
        r = self.results
        if not r:
            return "请先运行分析"

        lines = []
        lines.append("=" * 55)
        lines.append("中介效应分析结果")
        lines.append("=" * 55)

        if r['type'] == 'simple':
            lines.append(f"\n模型: 单中介 (X→M→Y)")
            lines.append(f"X: {r['x']}  M: {r['m']}  Y: {r['y']}")
            lines.append(f"\n路径系数:")
            for k, v in r['paths'].items():
                lines.append(f"  {k:20s}  {v:+.4f}")
            lo, hi = r['ci']['lo'], r['ci']['hi']
            lines.append(f"\nBootstrap CI ({r['ci']['n']}次): [{lo:.4f}, {hi:.4f}]")
            lines.append(f"Sobel Z={r['sobel']['z']:.3f}, p={r['sobel']['p']:.4f}")
            lines.append(f"中介效应占比: {r['ratio']:.1%}")
        else:
            lines.append(f"\n模型: 串行中介 (X→M1→M2→Y)")
            lines.append(f"X: {r['x']}  M1: {r['m1']}  M2: {r['m2']}  Y: {r['y']}")
            lines.append(f"\n路径系数:")
            for k, v in r['paths'].items():
                lines.append(f"  {k:20s}  {v:+.4f}")
            lines.append(f"\n间接效应:")
            for k, v in r['indirect'].items():
                lines.append(f"  {k:25s}  {v:+.4f}")
            lines.append(f"\nBootstrap CI ({r['ci']['n']}次):")
            for k in ['ind1', 'ind2', 'ind3']:
                lo, hi = r['ci'][k]
                lines.append(f"  {k}: [{lo:.4f}, {hi:.4f}]")

        lines.append("\n" + "=" * 55)
        return "\n".join(lines)

    def r_code(self):
        r = self.results
        if not r:
            return "# 请先运行分析"
        if r['type'] == 'simple':
            return self._r_simple(r)
        return self._r_serial(r)

    def _r_simple(self, r):
        x, m, y = r['x'], r['m'], r['y']
        return f'''library(lavaan)

model <- "
  {y} ~ c*{x}
  {m} ~ a*{x}
  {y} ~ b*{m}
  indirect := a*b
  total := c + a*b
"

fit <- sem(model, data = df, se = "bootstrap", bootstrap = 5000)
summary(fit, standardized = TRUE, fit.measures = TRUE)
parameterEstimates(fit, standardized = TRUE)
'''

    def _r_serial(self, r):
        x, m1, m2, y = r['x'], r['m1'], r['m2'], r['y']
        return f'''library(lavaan)

model <- "
  {y} ~ c*{x}
  {m1} ~ a1*{x}
  {m2} ~ a2*{x}
  {m2} ~ d21*{m1}
  {y} ~ b1*{m1}
  {y} ~ b2*{m2}
  ind1 := a1*b1
  ind2 := a2*b2
  ind3 := a1*d21*b2
"

fit <- sem(model, data = df, se = "bootstrap", bootstrap = 5000)
summary(fit, standardized = TRUE, fit.measures = TRUE)
parameterEstimates(fit, standardized = TRUE)
'''


def load_data(path):
    import os
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    if path.endswith('.csv'):
        return pd.read_csv(path)
    if path.endswith(('.xlsx', '.xls')):
        return pd.read_excel(path)
    raise ValueError(f"不支持的格式: {path}")


if __name__ == "__main__":
    np.random.seed(42)
    n = 200
    X = np.random.randn(n)
    M1 = 0.5 * X + np.random.randn(n) * 0.5
    M2 = 0.3 * X + 0.4 * M1 + np.random.randn(n) * 0.5
    Y = 0.2 * X + 0.3 * M1 + 0.4 * M2 + np.random.randn(n) * 0.5
    df = pd.DataFrame({'X': X, 'M1': M1, 'M2': M2, 'Y': Y})

    a = MediationAnalyzer(df, bootstrap_n=1000)
    a.simple_mediation('X', 'M1', 'Y')
    print(a.summary())

    a.serial_mediation('X', 'M1', 'M2', 'Y')
    print(a.summary())
