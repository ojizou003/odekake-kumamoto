import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import io # Excel出力のために追加

# --- 定数定義 ---
TARGET_URL = "https://kumanichi.com/event"

# --- スクレイピング処理 ---
def scrape_kumanichi_events():
    options = Options()
    options.add_argument("--headless")

    browser = webdriver.Chrome(options=options)
    browser.get(TARGET_URL)
    browser.implicitly_wait(10)

    info = browser.find_element(By.CLASS_NAME, "y2024-card-group")
    events = info.find_elements(By.TAG_NAME, "li")

    event_data = []
    for event in events:
        title = event.find_element(By.CLASS_NAME, "y2024-card__heading").text
        date = event.find_elements(By.CLASS_NAME, "y2024-text-01")[0].text
        try:
            location = event.find_elements(By.CLASS_NAME, "y2024-text-01")[1].text.replace('\u3000', ' ')
        except:
            location = "詳細はイベントURL参照"
        url = event.find_element(By.TAG_NAME, "a").get_attribute('href')
        event_data.append({
            "イベントタイトル": title,
            "期日・期間": date,
            "開催場所": location,
            "イベントURL": url
        })
    event_df = pd.DataFrame(event_data)
    browser.quit()

    return event_df

# --- Streamlit アプリケーション ---
def main():
    st.set_page_config(page_title="熊本お出かけ情報一覧", layout="wide", initial_sidebar_state="expanded")

    # --- サイドバー ---
    st.sidebar.title("🏞️熊本お出かけナビ")
    st.sidebar.markdown(f"情報元:\n{TARGET_URL}")

    if st.sidebar.button("お出かけ情報を取得する", type="primary"):
        st.session_state.data_loaded = True # ボタンが押されたことを記録
        with st.spinner("イベント情報を取得中... 1分ほどお待ちください。"):
            st.session_state.df_events = scrape_kumanichi_events() # 結果をセッション状態に保存
    
    st.sidebar.markdown("---")

    st.sidebar.image("aso-kumamon.jpg")
    st.sidebar.markdown("<div style='text-align: right;'>© 2025 ojizou003</div>", unsafe_allow_html=True)

    # --- メインコンテンツ ---
    st.title("📅 熊本お出かけ情報")

    # セッション状態にデータがあれば表示
    if 'data_loaded' in st.session_state and st.session_state.data_loaded:
        df_events = st.session_state.get('df_events', pd.DataFrame()) # 保存されたデータを取得
        if not df_events.empty:
            st.subheader("イベントリスト")
            df_display = df_events[["イベントタイトル", "期日・期間", "開催場所", "イベントURL"]]
            df_display.index = range(1, len(df_display) + 1) # インデックスを1から始まるように設定
            st.dataframe(
                df_display,
                use_container_width=True,
                height=600, # 高さを指定して見やすく
                column_config={
                    "イベントURL": st.column_config.LinkColumn(
                        "イベントURL", display_text="詳細を見る" # オプション: リンクの表示テキストを変更
                    )
                }
            )

            st.markdown("---") # ダウンロードセクションの区切り
            st.subheader("📥 ダウンロード")
            
            col1, col2 = st.columns(2) # レイアウト調整用

            with col1:
                download_format = st.radio(
                    "ファイル形式を選択してください:",
                    ('CSV', 'Excel'),
                    horizontal=True,
                    label_visibility="collapsed" # ラベルを非表示にしてスッキリさせる
                )

            with col2:
                if download_format == 'CSV':
                    csv_data = df_display.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="💾 CSVファイルとしてダウンロード",
                        data=csv_data,
                        file_name="kumamoto_odekake_joho.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                elif download_format == 'Excel':
                    output = io.BytesIO()
                    # df_display.to_excel(output, index=False, sheet_name='イベント情報', engine='openpyxl')
                    # header=Falseとするとヘッダーなしになるので注意。index=FalseはDataFrameのindexを出力しない設定。
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_display.to_excel(writer, index=False, sheet_name='イベント情報')
                    excel_data = output.getvalue()
                    st.download_button(
                        label="💾 Excelファイルとしてダウンロード",
                        data=excel_data,
                        file_name="kumamoto_odekake_joho.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

        # scrape_kumanichi_events関数内でエラー/情報メッセージが表示されるので、ここでは追加メッセージは最小限に
    else:
        st.info("サイドバーの「お出かけ情報を取得する」ボタンを押して、最新情報を取得してください。")

if __name__ == "__main__":
    main()
