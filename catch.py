import os
import re
import time
from playwright.sync_api import sync_playwright

def monitor_soxl_ultra():
    url = "https://www.gate.com/zh/orderbook/futures/usdt/SOXL_USDT?unit=unit"
    txt_file = "soxl_log_2026_06_08.txt"
    
    # 初始化文件
    if not os.path.exists(txt_file):
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("Timestamp | Last_Price | Buy_Price | Sell_Price | Buy_Ratio | Sell_Ratio | B-S_Diff\n")

    print(" 正在启动浏览器...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=60000)
            print("📢 请在浏览器中完成滑块验证（如存在）。")

            # 等待关键元素加载
            page.wait_for_selector('.trade_up.font-subtitle', timeout=30000)
            print("⚡ 页面加载完成，开始监控...\n")

            num_pattern = re.compile(r"(\d+\.\d+)")

            # JS 提取器 - 根据实际 HTML 结构
            js_extractor = """
            () => {
                // 最新成交价
                let priceElem = document.querySelector('.trade_up.font-subtitle');
                let price = priceElem ? priceElem.innerText.trim() : "";
                
                // 卖一价 (asks 第一个)
                let askElem = document.querySelector('div[type="asks"] .styled__PriceItem-sc-802dfbfa-4');
                let askPrice = askElem ? askElem.innerText.trim() : "";
                
                // 买一价 (bids 第一个)
                let bidElem = document.querySelector('div[type="bids"] .styled__PriceItem-sc-802dfbfa-4');
                let bidPrice = bidElem ? bidElem.innerText.trim() : "";
                
                // 买入比例
                let buyElem = document.querySelector('div[type="buy"]');
                let buyRatio = buyElem ? buyElem.innerText.trim() : "";
                
                // 卖出比例
                let sellElem = document.querySelector('div[type="sell"]');
                let sellRatio = sellElem ? sellElem.innerText.trim() : "";
                
                return {
                    price: price,
                    ask: askPrice,
                    bid: bidPrice,
                    buy: buyRatio,
                    sell: sellRatio
                };
            }
            """

            last_price = "0.00"
            last_ask = "0.00"
            last_bid = "0.00"
            last_buy_ratio = 50.0
            last_sell_ratio = 50.0

            with open(txt_file, "a", buffering=1, encoding="utf-8") as txt_writer:
                while True:
                    start_time = time.time()

                    try:
                        raw_data = page.evaluate(js_extractor)

                        # 提取数字
                        price_match = num_pattern.search(raw_data["price"])
                        ask_match = num_pattern.search(raw_data["ask"])
                        bid_match = num_pattern.search(raw_data["bid"])
                        buy_match = num_pattern.search(raw_data["buy"])
                        sell_match = num_pattern.search(raw_data["sell"])

                        # 更新数据
                        price_str = price_match.group(1) if price_match else last_price
                        ask_str = ask_match.group(1) if ask_match else last_ask
                        bid_str = bid_match.group(1) if bid_match else last_bid
                        buy_ratio = float(buy_match.group(1)) if buy_match else last_buy_ratio
                        sell_ratio = float(sell_match.group(1)) if sell_match else last_sell_ratio

                        last_price, last_ask, last_bid = price_str, ask_str, bid_str
                        last_buy_ratio, last_sell_ratio = buy_ratio, sell_ratio

                        # 计算差值
                        imbalance_diff = buy_ratio - sell_ratio

                        # 时间戳
                        now = time.time()
                        current_time = f"{time.strftime('%H:%M:%S', time.localtime(now))}.{int((now % 1) * 1000):03d}"

                        # 写入文件
                        log_line = f"{current_time} | {price_str} | {bid_str} | {ask_str} | {buy_ratio:.2f}% | {sell_ratio:.2f}% | {imbalance_diff:+.2f}%\n"
                        txt_writer.write(log_line)

                        # 控制台显示
                        direction = "🟢 多头强" if imbalance_diff > 5 else ("🔴 空头强" if imbalance_diff < -5 else " 均衡")
                        print(f"\r实时监测 -> 时: {current_time} | 价: {price_str} | 买: {bid_str} | 卖: {ask_str} | 差值: {imbalance_diff:+.2f}% [{direction}] ", end="", flush=True)

                    except Exception as e:
                        print(f"\n⚠️ 提取失败: {e}")

                    # 控制频率 (50ms)
                    elapsed_time = time.time() - start_time
                    sleep_time = 0.05 - elapsed_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            print(f"\n 运行中断: {e}")
        finally:
            input("\n按回车键退出程序...")
            browser.close()

if __name__ == "__main__":
    monitor_soxl_ultra()