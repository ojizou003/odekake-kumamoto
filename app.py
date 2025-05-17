import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService # 追加
from webdriver_manager.chrome import ChromeDriverManager # 追加
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import io # Excel出力のために追加

# --- 定数定義 ---
TARGET_URL = "https://kumanichi.com/event"

# --- スクレイピング処理 ---
def scrape_kumanichi_events():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")

    browser = None
    event_data = []
    error_messages = [] # 個別の軽微なエラーメッセージを収集

    try:
        # ChromeDriverを自動的にダウンロード・管理
        service = ChromeService(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=options)
        browser.set_page_load_timeout(30) # ページ読み込みタイムアウトを30秒に設定
        browser.get(TARGET_URL)
        browser.implicitly_wait(10) # 要素が見つかるまでの暗黙的な待機時間

        info_container = browser.find_element(By.CLASS_NAME, "y2024-card-group")
        event_elements = info_container.find_elements(By.TAG_NAME, "li")

        if not event_elements:
            st.warning("イベント情報が見つかりませんでした。ウェブサイトの構造が変更されたか、現在イベント情報がない可能性があります。")
            return pd.DataFrame([])

        for i, event_el in enumerate(event_elements):
            title, date, location, url = "取得失敗", "取得失敗", "詳細はイベントURL参照", "#"

            try:
                title_el = event_el.find_element(By.CLASS_NAME, "y2024-card__heading")
                title = title_el.text.strip() if title_el.text else "タイトルなし"
            except NoSuchElementException:
                error_messages.append(f"イベント {i+1}: タイトルが見つかりません。")

            try:
                details_els = event_el.find_elements(By.CLASS_NAME, "y2024-text-01")
                if len(details_els) > 0:
                    date = details_els[0].text.strip() if details_els[0].text else "日付情報なし"
                else:
                    error_messages.append(f"イベント '{title[:20]}...': 日付情報が見つかりません。")

                if len(details_els) > 1:
                    location = details_els[1].text.replace('\u3000', ' ').strip() if details_els[1].text else "場所情報なし"
                # locationのデフォルトは "詳細はイベントURL参照" のまま
            except NoSuchElementException: # find_elementsを使っているので稀だが念のため
                error_messages.append(f"イベント '{title[:20]}...': 日付/場所の親要素が見つかりません。")

            try:
                link_el = event_el.find_element(By.TAG_NAME, "a")
                url_attribute = link_el.get_attribute('href')
                if url_attribute:
                    url = url_attribute
                else:
                    error_messages.append(f"イベント '{title[:20]}...': URL属性が空です。")
            except NoSuchElementException:
                error_messages.append(f"イベント '{title[:20]}...': URLリンクが見つかりません。")

            event_data.append({
                "イベントタイトル": title,
                "期日・期間": date,
                "開催場所": location,
                "イベントURL": url
            })
    except WebDriverException as e:
        st.error(f"WebDriverエラーが発生しました: {e}\nChromeDriverのパスやバージョン、Chromeブラウザが正しくインストールされているか確認してください。")
        return pd.DataFrame([])
    except TimeoutException:
        st.error(f"ウェブサイト ({TARGET_URL}) の読み込みがタイムアウトしました。インターネット接続を確認するか、後で再試行してください。")
        return pd.DataFrame([])
    except NoSuchElementException as e:
        st.error(f"スクレイピングに必要な主要なページ要素が見つかりませんでした (エラー: {e.msg})。ウェブサイトの構造が変更された可能性があります。")
        return pd.DataFrame([])
    except Exception as e:
        st.error(f"スクレイピング中に予期せぬエラーが発生しました: {type(e).__name__} - {e}")
        return pd.DataFrame([])
    finally:
        if browser:
            browser.quit()

    for msg in error_messages:
        st.warning(msg)

    event_df = pd.DataFrame(event_data)

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
        st.info("サイドバーの「お出かけ情報を取得する」ボタンを押して、最新情報を表示してください。")

if __name__ == "__main__":
    main()
