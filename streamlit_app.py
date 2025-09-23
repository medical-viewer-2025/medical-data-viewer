import streamlit as st
import pandas as pd
import os
from datetime import datetime

# PDF 出力用
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 基本設定
st.set_page_config(
    layout="wide",
    page_title="医療データ閲覧ツール",
    page_icon="🏥",
    initial_sidebar_state="collapsed"
)

# レイアウト修正CSS
st.markdown("""
<style>
    /* サイドバーを完全に隠す */
    .css-1d391kg, .css-1544g2n, .css-1y4p8pa {
        display: none !important;
    }
    
    /* メインコンテンツエリアを最大幅に */
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: none !important;
        width: 100% !important;
    }
    
    /* Streamlitのデフォルトマージンをリセット */
    .main {
        padding: 0 !important;
    }
    
    /* ヘッダー部分の調整 */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    /* タブコンテナの幅調整 */
    .stTabs {
        width: 100%;
    }
    
    /* データフレームの表示調整 */
    .dataframe {
        width: 100% !important;
    }
    
    /* ファイルアップローダーの幅調整 */
    .uploadedFile {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 日本語フォント登録
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
except:
    st.warning("日本語フォントの読み込みに失敗しました。PDF出力で文字化けする可能性があります。")

# 保存フォルダ
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# =====================
# 認証機能
# =====================
def check_password():
    """パスワード認証を行う"""
    def password_entered():
        """パスワードが入力された時の処理"""
        correct_password = "medical2025"
        
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのためパスワードを削除
        else:
            st.session_state["password_correct"] = False

    # 認証状態の確認
    if "password_correct" not in st.session_state:
        # 初回アクセス時
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.title("🔐 医療データ閲覧ツール - ログイン")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### アクセスにはパスワードが必要です")
            st.text_input(
                "パスワードを入力してください", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="パスワードを入力"
            )
            st.info("パスワードは管理者から配布されたものを使用してください")
        return False
    elif not st.session_state["password_correct"]:
        # パスワードが間違っている場合
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.title("🔐 医療データ閲覧ツール - ログイン")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input(
                "パスワードを入力してください", 
                type="password", 
                on_change=password_entered, 
                key="password",
                placeholder="パスワードを入力"
            )
            st.error("❌ パスワードが正しくありません。もう一度入力してください。")
        return False
    else:
        # 認証成功
        return True

# =====================
# メイン認証チェック
# =====================
if not check_password():
    st.stop()

# =====================
# ユーティリティ関数
# =====================
def save_uploaded_file(uploaded_file, filename):
    """アップロードされたファイルを保存"""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def load_file_if_exists(filename):
    """保存済みファイルがあれば読み込む"""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            return pd.read_excel(path)
        except Exception as e:
            st.error(f"ファイル読み込みエラー: {filename} - {str(e)}")
            return None
    return None

def filter_a(df, start_num, end_num, start_month, end_month, keyword):
    result = df.copy()
    # 型統一：援助年月は6桁文字列として扱う
    result["援助年月"] = result["援助年月"].astype(str).str.zfill(6)

    if start_num:
        try:
            result = result[result["一連番号"] >= int(start_num)]
        except ValueError:
            st.error("開始番号は数字で入力してください")
            return result
            
    if end_num:
        try:
            result = result[result["一連番号"] <= int(end_num)]
        except ValueError:
            st.error("終了番号は数字で入力してください")
            return result

    if start_month:
        if len(start_month) == 6 and start_month.isdigit():
            result = result[result["援助年月"] >= str(start_month)]
        else:
            st.error("開始年月はYYYYMM形式（例：202401）で入力してください")
            return result
            
    if end_month:
        if len(end_month) == 6 and end_month.isdigit():
            result = result[result["援助年月"] <= str(end_month)]
        else:
            st.error("終了年月はYYYYMM形式（例：202401）で入力してください")
            return result

    if keyword:
        words = keyword.split()
        result = result[result.apply(
            lambda row: all(row.astype(str).str.contains(w, case=False, na=False).any() for w in words),
            axis=1
        )]

    return result

def filter_b(df, keyword):
    if keyword:
        words = keyword.split()
        return df[df.apply(
            lambda row: all(row.astype(str).str.contains(w, case=False, na=False).any() for w in words),
            axis=1
        )]
    return df

def dept_counts(df_b, df_master):
    dept_col = "統計上の診療科"

    # 前処理：文字列化して余分な空白を削除
    df_master[dept_col] = df_master[dept_col].astype(str).str.strip()
    df_b[dept_col] = df_b[dept_col].astype(str).str.strip()

    master_list = [d for d in df_master[dept_col].unique().tolist() if d.lower() != "nan"]

    counts = []
    for dept in master_list:
        num = df_b[df_b[dept_col] == dept].shape[0]
        counts.append((dept, num))

    return pd.DataFrame(counts, columns=["診療科", "人数"])

def export_pdf_a(dataframe):
    if dataframe.empty:
        return None
    try:
        filename = f"Adata_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        styleN = styles["Normal"]
        styleN.fontName = "HeiseiKakuGo-W5"
        styleN.fontSize = 10

        elements = []
        for _, row in dataframe.iterrows():
            for col in dataframe.columns:
                text = f"<b>{col}</b>: {row[col]}"
                elements.append(Paragraph(text, styleN))
            elements.append(Spacer(1, 12))
        doc.build(elements)
        return filename
    except Exception as e:
        st.error(f"PDF出力エラー: {str(e)}")
        return None

def export_pdf_b(df_b, df_master, mode="all"):
    try:
        dept_col = "統計上の診療科"
        filename = f"Bdata_{mode}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        styleH = styles["Heading3"]
        styleH.fontName = "HeiseiKakuGo-W5"
        styleN = styles["Normal"]
        styleN.fontName = "HeiseiKakuGo-W5"
        styleN.fontSize = 10

        elements = []
        counts = dept_counts(df_b, df_master)

        for _, row in counts.iterrows():
            dept, num = row["診療科"], row["人数"]
            if mode == "nonempty" and num == 0:
                continue
            elements.append(Paragraph(f"{dept}（{num}人）", styleH))

            subset = df_b[df_b[dept_col] == dept] if dept != "その他" else df_b[~df_b[dept_col].isin(df_master[dept_col])]
            for _, r in subset.iterrows():
                text = " / ".join([f"{col}:{r[col]}" for col in df_b.columns])
                elements.append(Paragraph(text, styleN))
            elements.append(Spacer(1, 12))
        doc.build(elements)
        return filename
    except Exception as e:
        st.error(f"PDF出力エラー: {str(e)}")
        return None

# =====================
# メインアプリケーション
# =====================
def main():
    # ヘッダー部分
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🏥 医療データ閲覧ツール")
        st.markdown("**A/Bデータの検索・閲覧・PDF出力**")
    with col2:
        st.write("")  # スペース調整
        if st.button("🚪 ログアウト", key="logout_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Aデータ", "🏥 Bデータ"])

    # -----------------
    # Aデータ
    # -----------------
    with tab1:
        st.header("📊 Aデータ閲覧")

        # 保存済みファイルを先にロード
        df_a = load_file_if_exists("A_data.xlsx")

        uploaded_a = st.file_uploader(
            "Aデータ Excelファイル（更新時のみアップロード）", 
            type=["xlsx"], 
            key="file_a"
        )
        
        if uploaded_a:
            with st.spinner("ファイルを処理中..."):
                save_uploaded_file(uploaded_a, "A_data.xlsx")
                df_a = pd.read_excel(os.path.join(DATA_DIR, "A_data.xlsx"))
                st.success("✅ Aデータを更新しました。")

        if df_a is not None:
            st.subheader("📋 全件リスト")
            st.info(f"総件数: {len(df_a)}件")
            st.dataframe(df_a, use_container_width=True, height=300)

            st.subheader("🔍 検索条件")
            
            col1, col2 = st.columns(2)
            with col1:
                start_num = st.text_input("開始番号", key="a_start_num", 
                                        value=st.session_state.get("a_start_num", ""))
                start_month = st.text_input("開始年月 (YYYYMM)", key="a_start_month", 
                                          value=st.session_state.get("a_start_month", ""))
            with col2:
                end_num = st.text_input("終了番号", key="a_end_num", 
                                      value=st.session_state.get("a_end_num", ""))
                end_month = st.text_input("終了年月 (YYYYMM)", key="a_end_month", 
                                        value=st.session_state.get("a_end_month", ""))
                
            keyword = st.text_input("🔎 キーワード検索", key="a_keyword", 
                                  value=st.session_state.get("a_keyword", ""))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 検索実行", key="a_search_btn"):
                    with st.spinner("検索中..."):
                        st.session_state["a_filtered"] = filter_a(df_a, start_num, end_num, start_month, end_month, keyword)
                        if not st.session_state["a_filtered"].empty:
                            st.success(f"✅ {len(st.session_state['a_filtered'])}件見つかりました")
                        else:
                            st.warning("⚠️ 検索条件に一致するデータがありませんでした")

            with col2:
                if st.button("🗑️ 検索条件クリア", key="a_clear_btn"):
                    for key in ["a_start_num", "a_end_num", "a_start_month", "a_end_month", "a_keyword", "a_filtered"]:
                        st.session_state.pop(key, None)
                    st.rerun()

            if "a_filtered" in st.session_state and isinstance(st.session_state["a_filtered"], pd.DataFrame):
                filtered_a = st.session_state["a_filtered"]
                st.subheader("📋 検索結果一覧")
                st.info(f"検索結果: {len(filtered_a)}件")
                st.dataframe(filtered_a, use_container_width=True, height=300)

                st.subheader("📄 検索結果詳細表示")
                for idx, record in enumerate(filtered_a.to_dict(orient="records")):
                    with st.expander(f"📄 {idx + 1}件目"):
                        for key, value in record.items():
                            st.write(f"**{key}**: {value}")

                if st.button("📑 PDF出力（検索結果のみ）", key="a_pdf_btn"):
                    with st.spinner("PDF生成中..."):
                        filename = export_pdf_a(filtered_a)
                        if filename:
                            st.success(f"✅ PDFを出力しました: {filename}")
                            with open(filename, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 PDFをダウンロード",
                                    data=pdf_file.read(),
                                    file_name=filename,
                                    mime="application/pdf"
                                )

    # -----------------
    # Bデータ
    # -----------------
    with tab2:
        st.header("🏥 Bデータ閲覧")

        df_master = load_file_if_exists("B_master.xlsx")
        df_b = load_file_if_exists("B_data.xlsx")

        col1, col2 = st.columns(2)
        with col1:
            uploaded_master = st.file_uploader(
                "Bデータ マスターExcelファイル", 
                type=["xlsx"], 
                key="file_master"
            )
            if uploaded_master:
                with st.spinner("マスターファイル処理中..."):
                    save_uploaded_file(uploaded_master, "B_master.xlsx")
                    df_master = pd.read_excel(os.path.join(DATA_DIR, "B_master.xlsx"))
                    st.success("✅ マスターファイルを更新しました。")

        with col2:
            uploaded_b = st.file_uploader(
                "Bデータ Excelファイル", 
                type=["xlsx"], 
                key="file_b"
            )
            if uploaded_b:
                with st.spinner("Bデータ処理中..."):
                    save_uploaded_file(uploaded_b, "B_data.xlsx")
                    df_b = pd.read_excel(os.path.join(DATA_DIR, "B_data.xlsx"))
                    st.success("✅ Bデータを更新しました。")

        if df_master is not None and df_b is not None:
            st.subheader("📋 全件リスト")
            st.info(f"総件数: {len(df_b)}件")
            st.dataframe(df_b, use_container_width=True, height=300)

            st.subheader("🔍 検索条件")
            col1, col2 = st.columns([3,1])
            with col1:
                keyword_b = st.text_input("🔎 キーワード検索", key="b_keyword", 
                                        value=st.session_state.get("b_keyword", ""))
            with col2:
                if st.button("🔍 検索", key="b_search_btn"):
                    with st.spinner("検索中..."):
                        st.session_state["b_filtered"] = filter_b(df_b, keyword_b)
                        if not st.session_state["b_filtered"].empty:
                            st.success(f"✅ {len(st.session_state['b_filtered'])}件見つかりました")

            if st.button("🗑️ 検索条件クリア", key="b_clear_btn"):
                for key in ["b_keyword", "b_filtered"]:
                    st.session_state.pop(key, None)
                st.rerun()

            if "b_filtered" in st.session_state and isinstance(st.session_state["b_filtered"], pd.DataFrame):
                filtered_b = st.session_state["b_filtered"]
                st.subheader("📋 検索結果一覧")
                st.info(f"検索結果: {len(filtered_b)}件")
                st.dataframe(filtered_b, use_container_width=True, height=300)

            st.subheader("🏥 診療科別統計")
            counts = dept_counts(df_b, df_master)
            
            for _, row in counts.iterrows():
                dept_data = df_b[df_b["統計上の診療科"] == row["診療科"]]
                with st.expander(f"🏥 {row['診療科']}（{row['人数']}人）"):
                    if not dept_data.empty:
                        st.dataframe(dept_data, use_container_width=True)
                    else:
                        st.info("該当するデータがありません")

            # その他のデータ
            other_df = df_b[~df_b["統計上の診療科"].isin(df_master["統計上の診療科"])]
            if not other_df.empty:
                with st.expander(f"❓ その他（{len(other_df)}人）"):
                    st.dataframe(other_df, use_container_width=True)

            st.subheader("📑 PDF出力")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 全診療科（人数0含む）", key="b_pdf_all"):
                    with st.spinner("PDF生成中..."):
                        filename = export_pdf_b(df_b, df_master, mode="all")
                        if filename:
                            st.success(f"✅ PDFを出力しました: {filename}")
                            with open(filename, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 PDFをダウンロード",
                                    data=pdf_file.read(),
                                    file_name=filename,
                                    mime="application/pdf",
                                    key="download_all"
                                )
            with col2:
                if st.button("📄 人数あり診療科のみ", key="b_pdf_nonempty"):
                    with st.spinner("PDF生成中..."):
                        filename = export_pdf_b(df_b, df_master, mode="nonempty")
                        if filename:
                            st.success(f"✅ PDFを出力しました: {filename}")
                            with open(filename, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 PDFをダウンロード",
                                    data=pdf_file.read(),
                                    file_name=filename,
                                    mime="application/pdf",
                                    key="download_nonempty"
                                )
        else:
            st.info("📁 マスターファイルとBデータファイルの両方をアップロードしてください")


if __name__ == "__main__":
    main()
