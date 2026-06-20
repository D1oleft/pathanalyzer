# PathAnalyzer

中介效应分析工具，支持简单中介、并行中介、串联中介和全链路扫描。

## 下载

直接下载 [PathAnalyzer.exe](PathAnalyzer.exe)，双击运行，不需要安装。

## 功能

- 简单中介分析 (X→M→Y)
- 并行中介分析 (X→M1/M2→Y)
- 串联中介分析 (X→M1→M2→Y)
- 全链路扫描（自动遍历所有X×M×Y组合）
- Bootstrap置信区间
- Sobel检验
- R代码生成 (lavaan)
- 智能解读
- Excel/Word导出

## 快速开始

1. 双击 PathAnalyzer.exe 启动软件
2. 点击「加载数据」选择Excel文件
3. 拖放变量到X、Y、M框
4. 选择模型类型（并行/串联）
5. 点击「运行分析」

详细步骤见 [快速开始指南](docs/快速开始指南.md) 或 [使用说明书](docs/PathAnalyzer_使用说明书.md)。

## 测试数据

tests/ 目录下有5个测试文件：

| 文件 | 模型 | 说明 |
|------|------|------|
| 测试1_简单中介.xlsx | 施氮量→硝态氮→产量 | 单中介 |
| 测试2_并行中介.xlsx | 施氮量→BG/NO3→产量 | 双中介并行 |
| 测试3_串联中介.xlsx | 施氮量→酶活性→硝态氮→产量 | 三链串联 |
| 测试4_二链全扫描.xlsx | 3X×3M×2Y=18条路径 | 全扫描 |
| 测试5_三链全扫描.xlsx | 2X×4M×2Y=16条路径 | 全扫描 |

## 文档

- [5个测试操作步骤](docs/5个测试操作步骤（老师先看这个）.docx)
- [使用说明书](docs/PathAnalyzer_使用说明书.docx)
- [快速开始指南](docs/快速开始指南.docx)

## 开发

Python源码版：

```bash
pip install -r requirements.txt
python main.py
```

## 技术栈

- Python 3.14
- tkinter (GUI)
- scipy (统计)
- pandas (数据处理)
- openpyxl (Excel)
- python-docx (Word)

## License

MIT
