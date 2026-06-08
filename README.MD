# SOXL High-Frequency Trading Analysis

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📊 项目简介

本项目是一个针对 SOXL (Direxion Daily Semiconductor Bull 3X ETF) 高频交易日志数据的分析与 Alpha 因子挖掘工具。项目提供了完整的数据清洗、多格式解析、时间序列重采样以及因子有效性检验（Rank IC 分析）功能，适用于量化交易研究、市场微观结构分析以及计算机数据科学教学演示。

## ✨ 主要功能

### 1. 鲁棒的多格式数据解析
- 自动识别并兼容**空格分隔**与**竖线 (`|`) 分隔**的混合日志格式。
- 内置异常处理机制，自动跳过表头粘连、格式损坏或包含非数字字符的脏数据行。

### 2. 专业的数据清洗与预处理
- 毫秒级时间戳标准化与排序。
- 针对高频数据中常见的 `0.00` 缺失价格，采用前向填充 (Forward Fill) 策略进行修复。

### 3. Alpha 因子构建 (Feature Engineering)
- **Factor_BS_Mean_5**: 过去 5 个 tick 的买卖差均值（捕捉短期动量）。
- **Factor_BS_Delta**: 买卖差的一阶差分（捕捉订单流加速度）。
- **Factor_Extreme**: 极端失衡虚拟变量（捕捉均值回归/反转信号）。
- **Factor_Cum_BS_5s**: 秒级维度下过去 5 秒的累积买卖压力。
- **Factor_Pulse**: 秒内极端脉冲因子（捕捉大单瞬间扫货/砸盘）。

### 4. 时间重采样 (Time Resampling)
- 将不规则的毫秒级 Tick 数据聚合为等间隔的秒级 K 线（如 `1s`, `500ms`）。
- 计算每秒的中间价 (Mid-Price)、平均买卖差及最大绝对脉冲，有效过滤微观噪音。

### 5. 因子有效性检验 (Rank IC Analysis)
- 计算 Spearman 秩相关系数 (Rank IC)，评估因子对未来收益率的预测能力。
- 输出直观的统计报告，辅助判断因子属于“动量型”还是“反转型”。

## 📦 安装说明

### 环境要求
- Python 3.8+
- pandas
- numpy

### 安装依赖
建议使用虚拟环境以保持依赖整洁：
```bash
python -m venv .venv
# Windows 激活虚拟环境
.venv\Scripts\activate
# macOS/Linux 激活虚拟环境
# source .venv/bin/activate

pip install pandas numpy