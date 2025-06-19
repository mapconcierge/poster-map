import streamlit as st
import pandas as pd
import io
import os
from geo_processor import process_csv_data

st.set_page_config(page_title="CSV正規化ツール", layout="wide")

# --- サイドバー: 設定項目 ---
st.sidebar.title("設定")
sleep_msec = st.sidebar.number_input("APIリクエスト間隔（ミリ秒）", min_value=0, max_value=5000, value=200, step=10)
normalize_digits = st.sidebar.checkbox("漢数字をアラビア数字に変換", value=True)
st.sidebar.markdown("---")
st.sidebar.subheader("2重APIチェック設定")
gsi_check = st.sidebar.checkbox("Google＋国土地理院API両方を使う", value=True)
gsi_distance = st.sidebar.number_input("座標ズレ閾値（メートル）", value=200, min_value=0, max_value=10000, step=10)
priority = st.sidebar.selectbox("閾値超時に優先するAPI", options=["gsi", "google"], format_func=lambda x: "国土地理院" if x=="gsi" else "Google")

st.title("📍 CSV正規化ツール")
st.write("ポスター掲示場所等のCSVを正規化し、Google Mapsを使って緯度経度を付与します。")

st.header("1. CSVファイルをアップロード")
csv_file = st.file_uploader("CSVファイルを選択してください", type=["csv"])
df = None
filename = ""
if csv_file is not None:
    df = pd.read_csv(csv_file)
    st.success(f"CSVファイルを読み込みました（{len(df)}行のデータ）")
    st.subheader("データプレビュー")
    st.dataframe(df, height=400)
    if hasattr(csv_file, "name"):
        filename = csv_file.name
    elif isinstance(csv_file, str):
        filename = os.path.basename(csv_file)
    else:
        filename = ""

# 判別関数
def guess_pref_city_vals(col_names, df, filename):
    pref_candidates = [c for c in col_names if any(x in c for x in ["都", "道", "府", "県"])]
    city_candidates = [c for c in col_names if any(x in c for x in ["市", "区", "町", "村"])]
    pref = ""
    city = ""
    if pref_candidates:
        pref_col = pref_candidates[0]
        pref = df[pref_col].iloc[0] if df is not None and pref_col in df.columns else ""
    filename_city = ""
    for token in ["市", "区", "町", "村"]:
        if token in filename:
            filename_city = filename.split(token)[0] + token
            break
    if filename_city:
        city = filename_city
    elif city_candidates:
        city_col = city_candidates[0]
        city = df[city_col].iloc[0] if df is not None and city_col in df.columns else ""
    return pref, city

pref_val = ""
city_val = ""
number_col_guess = ""
addr_col_guess = ""
name_col_guess = ""

col_names = []
if df is not None:
    col_names = df.columns.tolist()
    pref_val, city_val = guess_pref_city_vals(col_names, df, filename)
    # 番号列候補
    number_col_guess = next((c for c in col_names if "番号" in c or "No" in c or "NO" in c or "no" in c or "num" in c), col_names[0] if col_names else "")
    addr_col_guess = next((c for c in col_names if "住" in c), col_names[0] if col_names else "")
    name_col_guess = next((c for c in col_names if "名" in c), col_names[1] if len(col_names) > 1 else "")

st.header("2. 設定を構成")
# テキスト入力で都道府県・市区町村
pref_val = st.text_input("都道府県（prefecture:固定値）", value=pref_val)
city_val = st.text_input("市区町村（city:固定値）", value=city_val)
# プルダウンで列選択
number_col = st.selectbox("番号列（number）", col_names, index=col_names.index(number_col_guess) if number_col_guess in col_names else 0)
addr_col = st.selectbox("住所列（address）", col_names, index=col_names.index(addr_col_guess) if addr_col_guess in col_names else 0)
name_col = st.selectbox("名称列（name）", col_names, index=col_names.index(name_col_guess) if name_col_guess in col_names else 0)

# 出力対象の候補を動的に
output_candidates = ["number", "address", "name", "lat", "long"]
default_outputs = ["number", "address", "name", "lat", "long"]
output_columns = st.multiselect(
    "出力する列を選択してください",
    output_candidates,
    default=default_outputs
)

st.header("3. 処理を実行")
log_lines = []
log_box = st.empty()
def log_callback(msg):
    log_lines.append(msg)
    log_box.text_area("ログ", "\n".join(log_lines[-500:]), height=300)

if st.button("CSV正規化を実行"):
    if df is not None:
        try:
            colmap = {col: idx for idx, col in enumerate(df.columns)}
            config = {
                "format": {},
                "api": {
                    "sleep": sleep_msec
                },
                "normalize_address_digits": normalize_digits
            }
            # 番号/address/nameはマッピング、lat/longはテンプレ
            for col in output_columns:
                if col == "number":
                    config["format"]["number"] = f"{{{colmap[number_col]+1}}}"
                elif col == "address":
                    config["format"]["address"] = f"{{{colmap[addr_col]+1}}}"
                elif col == "name":
                    config["format"]["name"] = f"{{{colmap[name_col]+1}}}"
                elif col == "lat":
                    config["format"]["lat"] = "{lat}"
                elif col == "long":
                    config["format"]["long"] = "{long}"

            config["format"]["prefecture"] = pref_val
            config["format"]["city"] = city_val

            csv_data = df.values.tolist()
            st.info("処理中…しばらくお待ちください")
            results = process_csv_data(
                csv_data,
                config,
                progress_callback=None,
                log_callback=log_callback,
                gsi_check=gsi_check,
                gsi_distance=int(gsi_distance),
                priority=priority
            )
            # 出力カラム順: prefecture, city, [ユーザー選択]
            output_header = ["prefecture", "city"] + list(output_columns)
            out_df = pd.DataFrame(
                [
                    [row[results[0].index("prefecture")], row[results[0].index("city")]]
                    + [row[results[0].index(col)] for col in output_columns]
                    for row in results[1:]
                ],
                columns=output_header
            )
            st.success("処理完了！出力データをダウンロードできます")
            st.dataframe(out_df, height=400)
            csv_buf = io.StringIO()
            out_df.to_csv(csv_buf, index=False)
            st.download_button(
                "結果CSVをダウンロード",
                data=csv_buf.getvalue(),
                file_name="normalized_output.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"エラー: {str(e)}")
    else:
        st.warning("CSVファイルをアップロードしてください。")
