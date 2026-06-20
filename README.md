# PathAnalyzer

中介效应分析工具，支持单中介和串行中介模型。

## 安装

```bash
git clone https://github.com/D1oleft/pathanalyzer.git
cd pathanalyzer
pip install -r requirements.txt
```

## 使用

GUI界面：
```bash
python main.py
```

代码调用：
```python
from analyzer import MediationAnalyzer, load_data

data = load_data("data.csv")
a = MediationAnalyzer(data, bootstrap_n=5000)
a.simple_mediation('X', 'M', 'Y')
print(a.summary())
```

## 功能

- 单中介分析 (X→M→Y)
- 串行中介分析 (X→M1→M2→Y)
- Bootstrap置信区间
- Sobel检验
- R代码生成 (lavaan)
- Excel导出

## 模型

单中介：
```
X --a--> M --b--> Y
```
间接效应 = a × b

串行中介：
```
X --a1--> M1 --b1--> Y
 \         ↘d21    ↗b2
  \         M2---→/
   --a2-->--/
```
- ind1 = a1 × b1
- ind2 = a2 × b2
- ind3 = a1 × d21 × b2

## 参考

- Hayes (2013). Introduction to mediation, moderation, and conditional process analysis.
- Rosseel (2012). lavaan: An R Package for Structural Equation Modeling.

## License

MIT
