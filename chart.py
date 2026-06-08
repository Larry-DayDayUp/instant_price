import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import os

# ================= 1. 彻底解决中文方块问题 =================
# 优先使用微软雅黑（Windows 自带），其次黑体，最后回退到系统默认
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题

# 强制刷新 Matplotlib 字体缓存（防止旧缓存导致字体不生效）
fm._load_fontmanager(try_read_cache=False)

filename = 'soxl_log_2026_06_07.txt'

# ================= 2. 智能读取与表头处理 =================
df = pd.read_csv(filename, sep='|', skipinitialspace=True)
df.columns = df.columns.str.strip()

if 'Timestamp' in df.columns and str(df.iloc[0]['Timestamp']).strip() == 'Timestamp':
    df = df.iloc[1:].copy()
elif 'Timestamp' not in df.columns:
    df.columns = ['Timestamp', 'Last_Price', 'Buy_Price', 'Sell_Price', 'Buy_Ratio', 'Sell_Ratio', 'B-S_Diff']

cols = ['Timestamp', 'Last_Price', 'Buy_Ratio', 'Sell_Ratio', 'B-S_Diff']
df = df[cols].copy()

# ================= 3. 数据清洗与转换 =================
df['Last_Price'] = pd.to_numeric(df['Last_Price'], errors='coerce')
for col in ['Buy_Ratio', 'Sell_Ratio', 'B-S_Diff']:
    df[col] = df[col].astype(str).str.strip().str.replace('%', '', regex=False).str.replace('+', '', regex=False)
    df[col] = pd.to_numeric(df[col], errors='coerce')

# ================= 4. 时间序列处理 =================
df['Timestamp'] = pd.to_datetime('2026-06-07 ' + df['Timestamp'].astype(str).str.strip(), errors='coerce')
df = df.dropna(subset=['Timestamp'])
df.set_index('Timestamp', inplace=True)
df.sort_index(inplace=True)

# 按 15 秒降采样
df_resampled = df.resample('15s').mean().dropna()

if df_resampled.empty:
    print("❌ 错误：没有有效数据，请检查文件路径或内容。")
    exit()

# ================= 5. 绘制专业图表 =================
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True, 
                                    gridspec_kw={'height_ratios': [3, 1, 1]})

# 图1：价格走势
ax1.plot(df_resampled.index, df_resampled['Last_Price'], color='#1f77b4', linewidth=1.5, label='Last Price')
ax1.set_title('SOXL 价格走势与市场情绪分析 (2026-06-07)', fontsize=16, fontweight='bold')
ax1.set_ylabel('Price (USD)', fontsize=12)
ax1.grid(True, linestyle='--', alpha=0.4)
ax1.legend(loc='upper left')

# 图2：买卖比例
ax2.plot(df_resampled.index, df_resampled['Buy_Ratio'], color='#2ca02c', linewidth=1, label='Buy Ratio (买)')
ax2.plot(df_resampled.index, df_resampled['Sell_Ratio'], color='#d62728', linewidth=1, label='Sell Ratio (卖)')
ax2.fill_between(df_resampled.index, df_resampled['Buy_Ratio'], df_resampled['Sell_Ratio'], 
                 where=(df_resampled['Buy_Ratio'] >= df_resampled['Sell_Ratio']), color='#2ca02c', alpha=0.15)
ax2.fill_between(df_resampled.index, df_resampled['Buy_Ratio'], df_resampled['Sell_Ratio'], 
                 where=(df_resampled['Buy_Ratio'] < df_resampled['Sell_Ratio']), color='#d62728', alpha=0.15)
ax2.axhline(50, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
ax2.set_ylabel('Ratio (%)', fontsize=12)
ax2.grid(True, linestyle='--', alpha=0.4)
ax2.legend(loc='upper left')

# 图3：买卖价差
colors = ['#2ca02c' if x >= 0 else '#d62728' for x in df_resampled['B-S_Diff']]
ax3.bar(df_resampled.index, df_resampled['B-S_Diff'], color=colors, width=0.002, alpha=0.8)
ax3.axhline(0, color='black', linewidth=0.8)
ax3.set_ylabel('B-S Diff (%)', fontsize=12)
ax3.set_xlabel('Time', fontsize=12)
ax3.grid(True, linestyle='--', alpha=0.4)

ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax3.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
plt.gcf().autofmt_xdate()

# ================= 6. 核心：修复中文方块的同步光标 =================
vlines = []
for ax in [ax1, ax2, ax3]:
    vline = ax.axvline(x=df_resampled.index[0], color='gray', linestyle='--', linewidth=1, alpha=0.7, visible=False)
    vlines.append(vline)

# ️ 关键修复：移除了 fontfamily='monospace'，让浮窗使用全局的微软雅黑字体
text_box = ax1.text(0.02, 0.95, '', transform=ax1.transAxes, fontsize=11, 
                    verticalalignment='top', 
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='wheat', alpha=0.9, edgecolor='gray'),
                    visible=False, fontweight='bold')

def on_move(event):
    if event.inaxes in [ax1, ax2, ax3] and event.xdata is not None:
        target_time = mdates.num2date(event.xdata).replace(tzinfo=None)
        target_ts = pd.Timestamp(target_time)
        
        idx = df_resampled.index.searchsorted(target_ts)
        if idx >= len(df_resampled):
            idx = len(df_resampled) - 1
        elif idx > 0:
            t_prev = df_resampled.index[idx-1]
            t_curr = df_resampled.index[idx]
            if abs((target_ts - t_prev).total_seconds()) < abs((t_curr - target_ts).total_seconds()):
                idx = idx - 1
                
        t = df_resampled.index[idx]
        row = df_resampled.iloc[idx]
        
        for vline in vlines:
            vline.set_xdata([t, t])
            vline.set_visible(True)
            
        diff_val = row['B-S_Diff']
        diff_str = f"+{diff_val:.2f}%" if diff_val >= 0 else f"{diff_val:.2f}%"
        
        # 现在这里的汉字会正常显示为微软雅黑
        text_str = (f"时间: {t.strftime('%H:%M:%S')}\n"
                    f"价格: {row['Last_Price']:.2f}\n"
                    f"买盘: {row['Buy_Ratio']:.2f}%  |  卖盘: {row['Sell_Ratio']:.2f}%\n"
                    f"买卖差: {diff_str}")
        
        text_box.set_text(text_str)
        text_box.set_visible(True)
        fig.canvas.draw_idle()

def on_leave(event):
    for vline in vlines:
        vline.set_visible(False)
    text_box.set_visible(False)
    fig.canvas.draw_idle()

fig.canvas.mpl_connect('motion_notify_event', on_move)
fig.canvas.mpl_connect('axes_leave_event', on_leave)

# ================= 7. 保存与显示 =================
plt.tight_layout()
output_file = 'soxl_analysis_cursor.png'
plt.savefig(output_file, dpi=300)
print(f"✅ 图表已成功生成并保存为: {os.path.abspath(output_file)}")
print("💡 提示：请在弹出的图表窗口中移动鼠标，查看正常的中文显示效果！")

plt.show() 