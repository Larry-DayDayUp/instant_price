import pandas as pd
import numpy as np

def load_and_resample_log(file_path):
    print(f"[*] 正在读取并重采样文件: {file_path}")
    data = []
    
    # 1. 读取原始 Tick 数据
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or 'Timestamp' in line: continue
                
                try:
                    if '|' in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 7:
                            timestamp = parts[0]
                            bid = float(parts[2])
                            ask = float(parts[3])
                            mid_price = (bid + ask) / 2.0
                            bs_diff = float(parts[6].replace('%', ''))
                            data.append([timestamp, mid_price, bs_diff])
                except ValueError:
                    continue
    except FileNotFoundError:
        print(f"[!] 错误: 找不到文件 '{file_path}'")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['Timestamp', 'Mid_Price', 'B-S_Diff'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
    df.set_index('Timestamp', inplace=True)
    df = df.sort_index()
    
    print(f"[*] 原始 Tick 数据量: {len(df)} 行")
    
    # 2. 【核心】时间重采样 (Resample) - 将毫秒级数据聚合为 1 秒 K 线
    # 你可以尝试改为 '500ms' 或 '2s' 来寻找最佳预测窗口
    TIME_BAR = '1s' 
    
    df_1s = pd.DataFrame()
    # 中间价取每秒的最后一个值（代表该秒末的真实价格）
    df_1s['Mid_Price'] = df['Mid_Price'].resample(TIME_BAR).last()
    # 买卖差取每秒的平均值（代表该秒内的整体订单流压力）
    df_1s['BS_Diff_Mean'] = df['B-S_Diff'].resample(TIME_BAR).mean()
    # 买卖差取每秒的最大绝对值（捕捉秒内的极端脉冲）
    df_1s['BS_Diff_Max_Abs'] = df['B-S_Diff'].resample(TIME_BAR).apply(lambda x: x.abs().max())
    
    # 丢弃没有成交的秒
    df_1s.dropna(inplace=True)
    print(f"[*] 重采样为 {TIME_BAR} K线后数据量: {len(df_1s)} 行")
    
    return df_1s

print("=== 开始执行 v4.0 时间重采样实战脚本 ===")
df = load_and_resample_log('soxl_log_2026_06_07.txt')

if not df.empty:
    # ==========================================
    # 3. 构建秒级 Alpha 因子
    # ==========================================
    # 因子 1: 过去 5 秒的累积买卖差 (衡量持续的单边压力)
    df['Factor_Cum_BS_5s'] = df['BS_Diff_Mean'].rolling(window=5).sum()
    
    # 因子 2: 秒内极端脉冲 (衡量是否有大单瞬间砸盘/扫货)
    df['Factor_Pulse'] = df['BS_Diff_Max_Abs'] * np.sign(df['BS_Diff_Mean'])
    
    # ==========================================
    # 4. 构建秒级 Label (预测未来价格)
    # ==========================================
    # 预测未来 5 秒的中间价收益率 (在秒级维度，5秒是一个合理的微观持仓周期)
    FUTURE_SECONDS = 5
    df['Label_Future_Return'] = df['Mid_Price'].pct_change(periods=FUTURE_SECONDS).shift(-FUTURE_SECONDS)
    
    df.dropna(inplace=True)
    
    # ==========================================
    # 5. 因子有效性检验 (Rank IC)
    # ==========================================
    print("\n" + "="*60)
    print(f"Alpha 因子对【未来 {FUTURE_SECONDS} 秒真实收益率】的预测能力 (Rank IC)")
    print("="*60)
    
    target_label = 'Label_Future_Return'
    factors_to_test = ['Factor_Cum_BS_5s', 'Factor_Pulse']
    
    for factor in factors_to_test:
        ic = df[factor].corr(df[target_label], method='spearman')
        print(f"因子: {factor:<20} | Rank IC: {ic:>6.4f} | 绝对值: {abs(ic):>6.4f}")
        
    print("="*60)
    print("[*] 结论: 在秒级维度下，如果 IC 绝对值 > 0.05，说明因子具备了实盘指导意义！")
    print("[*] 提示: 如果 IC 为正，说明是动量因子(追涨杀跌)；如果为负，说明是反转因子(高抛低吸)。")