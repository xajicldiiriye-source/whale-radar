import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta

# 1. إعداد الصفحة وتوسيعها بالكامل لعرض نظام الأعمدة الاحترافي
st.set_page_config(page_title="رادار الحيتان - شاشة البورصة", layout="wide", initial_sidebar_state="expanded")

# تصميم واجهة مستخدم مخصصة بالثيم الداكن الفخم
st.markdown("""
    <style>
    body { background-color: #0d1117; }
    .whale-alert { padding: 12px; border-radius: 6px; background-color: #1a233a; border-right: 4px solid #ffaa00; margin-bottom: 10px; text-align: right; }
    .monitor-card { padding: 10px; background: #161b22; border-radius: 6px; border: 1px solid #30363d; text-align: center; margin-bottom: 10px; }
    h5, h2, p { margin: 0px !important; padding: 0px !important; }
    </style>
    """, unsafe_style_html=True)

st.title("🖥️ رادار الأسهم الاحترافي | شاشة MFI للمراقبة")

# 2. القائمة الجانبية لإعدادات السهم والعمولات
st.sidebar.header("🎯 رادار المسح الفوري")
preset_stocks = {
    "أنابيب السعودية (2200)": "2200.SR",
    "الريدان (9630)": "9630.SR",
    "الراجحي (1120)": "1120.SR",
    "أرامكو (2222)": "2222.SR",
    "إنفيديا (NVDA)": "NVDA",
    "تسلا (TSLA)": "TSLA",
    "مخصصة (اكتب الرمز بالأسفل)": "CUSTOM"
}

selected_preset = st.sidebar.selectbox("🚀 اختر الشركة للمراقبة:", list(preset_stocks.keys()))

if preset_stocks[selected_preset] == "CUSTOM":
    ticker = st.sidebar.text_input("أدخل رمز السهم بدقة:", "2200.SR").upper()
else:
    ticker = preset_stocks[selected_preset]

st.sidebar.markdown("---")
st.sidebar.subheader("💰 حاسبة السيولة والعمولة")
capital = st.sidebar.number_input("المبلغ المرصود للصفقة:", value=20000, step=5000)
commission_pct = st.sidebar.number_input("عمولة وسيطك (%):", value=0.155, format="%.3f")

period = st.sidebar.selectbox("📅 النطاق التاريخي للبيانات:", ["3mo", "6mo", "1y"], index=1)

@st.cache_data(ttl=15)
def load_live_data(symbol, p):
    try:
        data = yf.download(symbol, period=p, interval="1d")
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return None

with st.spinner("📡 جاري مسح السوق وتقسيم الأعمدة فنيّاً..."):
    df = load_live_data(ticker, period)

if df is not None and len(df) > 20:
    # 3. العمليات الحسابية لمؤشرات الحيتان والسيولة
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Ratio'] = df['Volume'] / df['Vol_SMA20']
    
    high_ser = df['High'].squeeze()
    low_ser = df['Low'].squeeze()
    close_ser = df['Close'].squeeze()
    open_ser = df['Open'].squeeze()
    vol_ser = df['Volume'].squeeze()
    
    df['MFI'] = ta.volume.money_flow_index(high_ser, low_ser, close_ser, vol_ser, window=14)
    df['EMA9'] = ta.trend.ema_indicator(close_ser, window=9)
    df['EMA21'] = ta.trend.ema_indicator(close_ser, window=21)

    df['Whale_Entry'] = (df['Vol_Ratio'] >= 2.0) & (close_ser > open_ser)
    df['Whale_Exit'] = (df['Vol_Ratio'] >= 2.0) & (close_ser < open_ser)

    last_vol_ratio = float(df['Vol_Ratio'].iloc[-1])
    last_close = float(df['Close'].iloc[-1])
    last_mfi = float(df['MFI'].iloc[-1])
    last_ema9 = float(df['EMA9'].iloc[-1])
    last_ema21 = float(df['EMA21'].iloc[-1])
    last_whale_entry = bool(df['Whale_Entry'].iloc[-1])
    last_whale_exit = bool(df['Whale_Exit'].iloc[-1])

    # 4. بناء هيكل الأعمدة الرئيسي
    chart_col, data_col = st.columns([72, 28])

    with chart_col:
        st.markdown("### 📈 الرسم البياني التفاعلي ورصد التدفقات")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.68, 0.32])

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="السعر"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='#00FFCC', width=1.2), name="EMA 9 (سريع)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='#FF007F', width=1.2), name="EMA 21 (بطيء)"), row=1, col=1)

        whales_in = df[df['Whale_Entry'] == True]
        whales_out = df[df['Whale_Exit'] == True]
        
        fig.add_trace(go.Scatter(x=whales_in.index, y=whales_in['Low'] * 0.96, mode='markers', marker=dict(symbol='star', size=13, color='#FFD700'), name='🐋 دخول حوت'), row=1, col=1)
        fig.add_trace(go.Scatter(x=whales_out.index, y=whales_out['High'] * 1.04, mode='markers', marker=dict(symbol='x', size=13, color='#FF0055'), name='🚨 تصريف حوت'), row=1, col=1)

        colors = ['#FFD700' if row['Whale_Entry'] else ('#FF0055' if row['Whale_Exit'] else '#30363d') for _, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='حجم السيولة'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_SMA20'], line=dict(color='#ffaa00', dash='dash'), name='متوسط 20 يوم'), row=2, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, height=680, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

    with data_col:
        st.markdown("### 🖥️ كابينة المراقبة اللحظية")
        if last_whale_entry:
            st.markdown(f"<div class='whale-alert' style='border-right-color: #00ffcc; color: #00ffcc;'>⚡ <b>إنذار:</b> رصد دخول حوت 🐋 سيولة ضخمة تجاوزت المعدل بـ {last_vol_ratio:.1f} ضعف!</div>", unsafe_style_html=True)
        elif last_whale_exit:
            st.markdown(f"<div class='whale-alert' style='border-right-color: #ff0055; color: #ff0055;'>🚨 <b>تحذير:</b> الحيتان تصرف! سيولة بيع تجاوزت المعدل بـ {last_vol_ratio:.1f} ضعف!</div>", unsafe_style_html=True)
        else:
            st.markdown(f"<div class='whale-alert' style='border-right-color: #718096; color: #a0aec0;'>🔄 سيولة طبيعية حالياً ({last_vol_ratio:.1f}x). صناع السوق هادئون اليوم.</div>", unsafe_style_html=True)

        st.markdown(f"<div class='monitor-card'><p style='color:#718096; font-size:13px;'>السعر الحالي</p><h2 style='color:#00ffcc;'>{last_close:.2f}</h2></div>", unsafe_style_html=True)
        st.markdown(f"<div class='monitor-card'><p style='color:#718096; font-size:13px;'>معدل السيولة الحالي</p><h2 style='color:#ffaa00;'>{last_vol_ratio:.2f}x</h2></div>", unsafe_style_html=True)
        st.markdown(f"<div class='monitor-card'><p style='color:#718096; font-size:13px;'>تدفق الأموال MFI</p><h2 style='color:#a020f0;'>{last_mfi:.1f}</h2></div>", unsafe_style_html=True)
        
        trend_status = "صاعد 📈" if last_ema9 > last_ema21 else "هابط 📉"
        trend_color = "#00ffcc" if "صاعد" in trend_status else "#ff0055"
        st.markdown(f"<div class='monitor-card'><p style='color:#718096; font-size:13px;'>الاتجاه اللحظي للرادار</p><h3 style='color:{trend_color};'>{trend_status}</h3></div>", unsafe_style_html=True)

        st.markdown("##### 📋 كشف حركات الهوامير السابقة")
        whale_history = df[(df['Whale_Entry']) | (df['Whale_Exit'])].copy()
        if not whale_history.empty:
            whale_history['الحركة'] = whale_history.apply(lambda r: '🐳 شراء' if r['Whale_Entry'] else '🚨 بيع', axis=1)
            whale_history['السيولة'] = whale_history['Vol_Ratio'].map("{:.1f}x".format)
            report_df = whale_history[['Close', 'السيولة', 'الحركة']].sort_index(ascending=False).head(8)
            st.dataframe(report_df, use_container_width=True, height=180)
        else:
            st.info("لا توجد حركات مريبة مسجلة تاريخياً.")
else:
    st.error("⚠️ خطأ في الاتصال برادار البورصة، تأكد من إدخال رمز السهم بالشكل الصحيح.")
