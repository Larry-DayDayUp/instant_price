import pandas as pd
import numpy as np

# ==========================================
# 1. 兼容多格式且防崩溃的数据读取函数
# ==========================================
def load_mixed_format_log(file_path):
    data = []
    # 尝试 utf-8 读取，如果报错可改为 encoding='gbk'
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 【修复点 1】：显式跳过包含表头关键字的行
            if 'Timestamp' in line or 'Last_Price' in line:
                continue
            
            try:
                if '|' in line:
                    # 处理格式 B: 19:50:02.807| 196.29| 196.22| 196.29| 30.25%| 69.75%| -39.50%
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 7:
                        timestamp = parts[0]
                        # parts[3] 通常是最新成交价 (Last Price)
                        last_price = float(parts[3].replace('%', ''))
                        buy_ratio = float(parts[4].replace('%', ''))
                        sell_ratio = float(parts[5].replace('%', ''))
                        bs_diff = float(parts[6].replace('%', ''))
                        data.append([timestamp, last_price, buy_ratio, sell_ratio, bs_diff])
                else:
                    # 处理格式 A: 19:20:51.147 0.00 41.88 58.12 -16.24
                    parts = line.split()
                    if len(parts) >= 5:
                        timestamp = parts[0]
                        last_price = float(parts[1])
                        buy_ratio = float(parts[2])
                        sell_ratio = float(parts[3])
                        bs_diff = float(parts[4])
                        data.append([timestamp, last_price, buy_ratio, sell_ratio, bs_diff])
            except (ValueError, IndexError):
                # 【修复点 2】：静默跳过任何无法解析的异常行（如表头与数据粘连、损坏的行）
                continue
                
    # 构建 DataFrame
    df = pd.DataFrame(data, columns=['Timestamp', 'Last_Price', 'Buy_Ratio', 'Sell_Ratio', 'B-S_Diff'])
    return df

print("正在读取并解析数据，请稍候...")
df = load_mixed_format_log('soxl_log_2026_06_07.txt')
print(f"数据加载成功！共解析 {len(df)} 行有效数据。")

# ==========================================
# 2. 数据清洗与预处理
# ==========================================
# 2.1 将 Timestamp 设为索引，方便后续按时间序列处理
# errors='coerce' 会将无法解析的时间转为 NaT，方便后续 dropna 清理
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
df.set_index('Timestamp', inplace=True)
df = df.sort_index() # 确保时间严格递增

# 2.2 处理 Last_Price 为 0.00 的问题
# 高频数据中，0.00 通常代表“该 tick 无最新成交，价格未更新”。
# 标准做法是使用前向填充 (Forward Fill)，用上一次的有效价格填补。
df['Last_Price'] = df['Last_Price'].replace(0.0, np.nan).ffill()

# ==========================================
# 3. Alpha 因子构建 (Feature Engineering)
# ==========================================
# 因子 1: B-S_Diff 的短期动量 (过去 5 个 tick 的均值)
df['Factor_BS_Mean_5'] = df['B-S_Diff'].rolling(window=5).mean()

# 因子 2: B-S_Diff 的加速度 (一阶差分)
df['Factor_BS_Delta'] = df['B-S_Diff'].diff()

# 因子 3: 极端失衡虚拟变量 (Extreme Imbalance Dummy)
# 逻辑：当 B-S_Diff 超过历史 90% 分位数时，标记为 1 (极度过买)，低于 10% 标记为 -1 (极度过卖)
upper_threshold = df['B-S_Diff'].quantile(0.90)
lower_threshold = df['B-S_Diff'].quantile(0.10)
df['Factor_Extreme'] = np.where(df['B-S_Diff'] > upper_threshold, 1, 
                       np.where(df['B-S_Diff'] < lower_threshold, -1, 0))

# ==========================================
# 4. 目标变量 (Label) 构建
# ==========================================
N_STEPS = 3 # 预测未来 3 个 tick 的表现