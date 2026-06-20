import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import numpy as np
import pandas as pd

from analyzer import MediationAnalyzer, load_data


class App:
    def __init__(self, root):
        self.root = root
        root.title("PathAnalyzer")
        root.geometry("1100x700")

        self.data = None
        self.analyzer = None

        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.m1_var = tk.StringVar()
        self.m2_var = tk.StringVar()
        self.model_var = tk.StringVar(value="simple")
        self.boot_var = tk.StringVar(value="5000")

        left = ttk.Frame(root, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)

        # 文件
        f = ttk.LabelFrame(left, text="数据", padding=4)
        f.pack(fill=tk.X, pady=(0, 8))
        self.file_lbl = ttk.Label(f, text="未加载")
        self.file_lbl.pack(fill=tk.X)
        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_row, text="打开文件", command=self.open_file).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="示例数据", command=self.load_example).pack(side=tk.LEFT, padx=4)

        # 变量选择
        v = ttk.LabelFrame(left, text="变量", padding=4)
        v.pack(fill=tk.X, pady=(0, 8))
        self.combos = {}
        for label, var in [("X", self.x_var), ("Y", self.y_var),
                           ("M1", self.m1_var), ("M2", self.m2_var)]:
            row = ttk.Frame(v)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label, width=4).pack(side=tk.LEFT)
            cb = ttk.Combobox(row, textvariable=var, state="readonly", width=15)
            cb.pack(side=tk.LEFT, padx=4)
            self.combos[label] = cb

        # 模型
        m = ttk.LabelFrame(left, text="模型", padding=4)
        m.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(m, text="单中介 (X→M→Y)",
                        variable=self.model_var, value="simple").pack(anchor=tk.W)
        ttk.Radiobutton(m, text="串行中介 (X→M1→M2→Y)",
                        variable=self.model_var, value="serial").pack(anchor=tk.W)

        # Bootstrap
        b = ttk.LabelFrame(left, text="Bootstrap", padding=4)
        b.pack(fill=tk.X, pady=(0, 8))
        row = ttk.Frame(b)
        row.pack(fill=tk.X)
        ttk.Label(row, text="次数:").pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.boot_var,
                     values=["1000", "5000", "10000"],
                     state="readonly", width=8).pack(side=tk.LEFT, padx=4)

        # 按钮
        ttk.Button(left, text="运行分析", command=self.run).pack(fill=tk.X, pady=(0, 4))
        btn_row2 = ttk.Frame(left)
        btn_row2.pack(fill=tk.X)
        ttk.Button(btn_row2, text="导出Excel", command=self.export_excel).pack(side=tk.LEFT)
        ttk.Button(btn_row2, text="复制R代码", command=self.copy_r).pack(side=tk.LEFT, padx=4)

        # 右侧结果
        right = ttk.Frame(root, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.txt_result = scrolledtext.ScrolledText(self.nb, wrap=tk.WORD)
        self.nb.add(self.txt_result, text="结果")
        self.txt_r = scrolledtext.ScrolledText(self.nb, wrap=tk.WORD)
        self.nb.add(self.txt_r, text="R代码")
        self.txt_interp = scrolledtext.ScrolledText(self.nb, wrap=tk.WORD)
        self.nb.add(self.txt_interp, text="解释")

        self.status = ttk.Label(root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("数据文件", "*.csv *.xlsx *.xls"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.data = load_data(path)
            self._update_combos()
            self.file_lbl.config(text=os.path.basename(path))
            self.status.config(text=f"已加载 {len(self.data)} 行")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def load_example(self):
        rng = np.random.default_rng(42)
        n = 200
        X = rng.standard_normal(n)
        M1 = 0.5 * X + rng.standard_normal(n) * 0.5
        M2 = 0.3 * X + 0.4 * M1 + rng.standard_normal(n) * 0.5
        Y = 0.2 * X + 0.3 * M1 + 0.4 * M2 + rng.standard_normal(n) * 0.5
        self.data = pd.DataFrame({'X': X, 'M1': M1, 'M2': M2, 'Y': Y})
        self._update_combos()
        self.x_var.set('X')
        self.y_var.set('Y')
        self.m1_var.set('M1')
        self.m2_var.set('M2')
        self.file_lbl.config(text="示例数据")
        self.status.config(text="已加载示例数据")

    def _update_combos(self):
        cols = list(self.data.columns)
        for cb in self.combos.values():
            cb['values'] = cols

    def run(self):
        if self.data is None:
            messagebox.showwarning("提示", "请先加载数据")
            return

        x, y, m1 = self.x_var.get(), self.y_var.get(), self.m1_var.get()
        if not all([x, y, m1]):
            messagebox.showwarning("提示", "请选择 X, Y, M1")
            return

        try:
            boot_n = int(self.boot_var.get())
        except ValueError:
            boot_n = 5000
        self.analyzer = MediationAnalyzer(self.data, boot_n)

        try:
            if self.model_var.get() == "simple":
                self.analyzer.simple_mediation(x, m1, y)
            else:
                m2 = self.m2_var.get()
                if not m2:
                    messagebox.showwarning("提示", "串行中介需要选择 M2")
                    return
                self.analyzer.serial_mediation(x, m1, m2, y)
        except Exception as e:
            messagebox.showerror("错误", f"分析失败: {e}")
            return

        self._show_results()
        self.status.config(text="分析完成")

    def _show_results(self):
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, self.analyzer.summary())

        self.txt_r.delete("1.0", tk.END)
        self.txt_r.insert(tk.END, self.analyzer.r_code())

        self.txt_interp.delete("1.0", tk.END)
        self.txt_interp.insert(tk.END, self._interpret())

    def _interpret(self):
        r = self.analyzer.results
        if not r:
            return ""

        lines = ["结果解释", "=" * 40]

        if r['type'] == 'simple':
            a = r['paths']['a (X→M)']
            b = r['paths']['b (M→Y)']
            c = r['paths']['c (总效应)']
            ab = r['paths']['ab (间接效应)']
            lo, hi = r['ci']['lo'], r['ci']['hi']

            lines.append(f"\n1. {r['x']}对{r['y']}的总效应为{c:.3f}")
            lines.append(f"2. {r['x']}通过{r['m']}的间接效应为{ab:.3f}")
            lines.append(f"3. Bootstrap 95%CI: [{lo:.3f}, {hi:.3f}]")
            if lo > 0 or hi < 0:
                lines.append("   → 区间不包含0，中介效应显著")
            else:
                lines.append("   → 区间包含0，中介效应不显著")
            lines.append(f"4. 中介效应占比: {r['ratio']:.1%}")
        else:
            lines.append(f"\n间接效应:")
            for k, v in r['indirect'].items():
                if k == 'total':
                    continue
                ci_key = k.split(' ')[0].lower()
                ci_lo, ci_hi = r['ci'][ci_key]
                sig = "显著" if (ci_lo > 0 or ci_hi < 0) else "不显著"
                lines.append(f"  {k}: {v:.3f} (CI [{ci_lo:.3f}, {ci_hi:.3f}], {sig})")

        lines.append("\n" + "=" * 40)
        return "\n".join(lines)

    def export_excel(self):
        if not self.analyzer or not self.analyzer.results:
            messagebox.showwarning("提示", "请先运行分析")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return

        try:
            r = self.analyzer.results
            rows = []
            for k, v in r['paths'].items():
                rows.append({'指标': k, '值': v})
            if r['type'] == 'serial':
                for k, v in r['indirect'].items():
                    rows.append({'指标': k, '值': v})
            pd.DataFrame(rows).to_excel(path, index=False)
            messagebox.showinfo("完成", f"已保存到 {path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def copy_r(self):
        if not self.analyzer:
            messagebox.showwarning("提示", "请先运行分析")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.analyzer.r_code())
        messagebox.showinfo("完成", "R代码已复制")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
