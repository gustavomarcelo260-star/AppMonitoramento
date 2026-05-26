import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Kopempack Operations Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CSS GLOBAL - TESLA OPS STYLE
# =========================================================
st.markdown("""
<style>

/* =========================================================
BACKGROUND
========================================================= */

html, body, [class*="css"] {
    font-family: "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: #070B14;
}

[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

/* =========================================================
SIDEBAR
========================================================= */

[data-testid="stSidebar"] {
    background: #0B111C;
    border-right: 1px solid #182234;
}

.sidebar-logo {
    text-align:center;
    padding-top:10px;
    padding-bottom:20px;
}

.sidebar-title {
    color:white;
    font-size:22px;
    font-weight:700;
    margin-top:15px;
}

.sidebar-subtitle {
    color:#6E7C93;
    font-size:13px;
}

/* =========================================================
HEADER HERO
========================================================= */

.hero-container {
    background: linear-gradient(135deg,#111827,#0B1220);
    border:1px solid #1B263B;
    padding:28px;
    border-radius:18px;
    margin-bottom:25px;
}

.hero-title {
    color:white;
    font-size:38px;
    font-weight:700;
    margin-bottom:8px;
}

.hero-subtitle {
    color:#8CA0B8;
    font-size:15px;
}

.hero-status {
    background:#0F1728;
    border:1px solid #1E2B45;
    padding:12px 18px;
    border-radius:12px;
    display:inline-block;
    margin-top:18px;
    color:#DCE6F2;
}

/* =========================================================
KPI CARDS
========================================================= */

.kpi-card {
    background: linear-gradient(180deg,#121A2B,#0D1422);
    border:1px solid #1E2B45;
    border-radius:18px;
    padding:24px;
    transition:0.3s;
    height:145px;
}

.kpi-card:hover {
    transform:translateY(-4px);
    border-color:#3B82F6;
}

.kpi-title {
    color:#7F93AD;
    font-size:13px;
    font-weight:600;
    letter-spacing:1px;
}

.kpi-value {
    color:white;
    font-size:42px;
    font-weight:700;
    margin-top:18px;
}

.kpi-blue {
    border-left:5px solid #3B82F6;
}

.kpi-green {
    border-left:5px solid #10B981;
}

.kpi-red {
    border-left:5px solid #EF4444;
}

.kpi-yellow {
    border-left:5px solid #F59E0B;
}

/* =========================================================
PANELS
========================================================= */

.panel {
    background:#0E1625;
    border:1px solid #1D2940;
    border-radius:18px;
    padding:20px;
    margin-top:15px;
}

.panel-title {
    color:white;
    font-size:18px;
    font-weight:600;
    margin-bottom:15px;
}

/* =========================================================
BUTTONS
========================================================= */

.stButton > button {
    width:100%;
    border-radius:12px !important;
    border:none !important;
    background:#2563EB !important;
    color:white !important;
    font-weight:600 !important;
    padding:12px !important;
}

.stButton > button:hover {
    background:#1D4ED8 !important;
}

/* =========================================================
INPUTS
========================================================= */

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] {
    background:#111827 !important;
    border:1px solid #1E293B !important;
    color:white !important;
    border-radius:10px !important;
}

/* =========================================================
TEXT
========================================================= */

h1,h2,h3,h4,h5 {
    color:white !important;
}

p,label {
    color:#CBD5E1 !important;
}

/* =========================================================
ALERT BOX
========================================================= */

.alert-box {
    background:#101826;
    border:1px solid #1F2A40;
    border-radius:14px;
    padding:18px;
    margin-bottom:12px;
}

.alert-title {
    color:white;
    font-weight:600;
}

.alert-sub {
    color:#8CA0B8;
    font-size:13px;
    margin-top:4px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# FIREBASE
# =========================================================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cert = dict(st.secrets["firebase"])
        cert["private_key"] = cert["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# =========================================================
# DATABASE FUNCTIONS
# =========================================================
def buscar_cilindros():
    docs = db.collection('cilindros_ativos').stream()
    lista = []
    for doc in docs:
        dado = doc.to_dict()
        dado['id_documento'] = doc.id
        lista.append(dado)
    return lista

def registrar_cilindro(payload):
    db.collection('cilindros_ativos').add(payload)

def atualizar_status_cilindro(id_documento, campos):
    db.collection('cilindros_ativos').document(id_documento).update(campos)

# =========================================================
# COMPONENTS
# =========================================================
def hero_header():
    horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">
            Kopempack Operations Center
        </div>
        <div class="hero-subtitle">
            Monitoramento industrial • Telemetria • Manutenção preditiva • Supervisão operacional
        </div>
        <div class="hero-status">
            🟢 Sistema Online • Última sincronização: {horario}
        </div>
    </div>
    """, unsafe_allow_html=True)

def kpi_card(titulo, valor, classe):
    st.markdown(f"""
    <div class="kpi-card {classe}">
        <div class="kpi-title">
            {titulo}
        </div>
        <div class="kpi-value">
            {valor}
        </div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# DASHBOARD
# =========================================================
def tela_dashboard():
    hero_header()
    cilindros = buscar_cilindros()

    if not cilindros:
        st.warning("Nenhum ativo cadastrado.")
        return

    df = pd.DataFrame(cilindros)

    if 'status' not in df.columns:
        df['status'] = 'NORMAL'

    if 'rul_percentual' not in df.columns:
        df['rul_percentual'] = 100

    total = len(df)
    alertas = len(df[df['status'] == 'ATENÇÃO'])
    falhas = len(df[df['status'] == 'FALHA IMINENTE'])
    media_rul = round(df['rul_percentual'].mean(), 1)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi_card("ATIVOS ONLINE", total, "kpi-blue")
    with c2:
        kpi_card("ALERTAS", alertas, "kpi-yellow")
    with c3:
        kpi_card("FALHAS CRÍTICAS", falhas, "kpi-red")
    with c4:
        kpi_card("HEALTH MÉDIO", f"{media_rul}%", "kpi-green")

    # =====================================================
    # CHARTS
    # =====================================================
    g1, g2 = st.columns([1,1])

    with g1:
        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        Status Operacional
        </div>
        """, unsafe_allow_html=True)

        fig = px.pie(
            df,
            names='status',
            hole=0.72,
            color='status',
            color_discrete_map={
                'NORMAL':'#3B82F6',
                'ATENÇÃO':'#F59E0B',
                'FALHA IMINENTE':'#EF4444'
            }
        )

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=420,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with g2:
        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        Integridade dos Ativos
        </div>
        """, unsafe_allow_html=True)

        df_sorted = df.sort_values(
            by='rul_percentual',
            ascending=True
        )

        fig2 = px.bar(
            df_sorted,
            x='rul_percentual',
            y='nome_identificacao',
            orientation='h',
            color='rul_percentual',
            color_continuous_scale=[
                '#EF4444',
                '#F59E0B',
                '#3B82F6'
            ]
        )

        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=420,
            xaxis_title="RUL %",
            yaxis_title=""
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # TABLE + EVENTS
    # =====================================================
    t1, t2 = st.columns([2,1])

    with t1:
        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        Ativos Monitorados
        </div>
        """, unsafe_allow_html=True)

        exibir = df[[
            'nome_identificacao',
            'tag_clp_vinculada',
            'estado_integridade',
            'rul_percentual',
            'status'
        ]]

        exibir.columns = [
            'Ativo',
            'Tag CLP',
            'Integridade',
            'RUL (%)',
            'Status'
        ]

        gb = GridOptionsBuilder.from_dataframe(exibir)
        gb.configure_default_column(
            groupable=True,
            value=True,
            enableRowGroup=True,
            editable=False
        )
        gridOptions = gb.build()

        AgGrid(
            exibir,
            gridOptions=gridOptions,
            height=420,
            fit_columns_on_grid_load=True,
            theme="streamlit"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        st.markdown("""
        <div class="panel">
        <div class="panel-title">
        Eventos Recentes
        </div>
        """, unsafe_allow_html=True)

        eventos = [
            ("🟢", "Sistema sincronizado", "Sem falhas detectadas"),
            ("🟡", "Vibração elevada", "Linha pneumática 02"),
            ("🔵", "Novo ativo registrado", "Comissionamento concluído"),
            ("🔴", "Falha crítica", "Necessária intervenção")
        ]

        for icon, titulo, sub in eventos:
            st.markdown(f"""
            <div class="alert-box">
                <div class="alert-title">
                    {icon} {titulo}
                </div>
                <div class="alert-sub">
                    {sub}
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# COMISSIONAMENTO
# =========================================================
def tela_comissionamento():
    hero_header()
    st.markdown("## Comissionamento Industrial")
    st.markdown("""Registro e sincronização de novos dispositivos industriais.""")

    col1, col2 = st.columns(2)

    tags_clp = [
        "SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04"
    ]

    tags_vib = [
        "SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04"
    ]

    with col1:
        st.markdown("### Vínculos Lógicos")
        tag_clp = st.selectbox("Tag CLP", tags_clp)
        tag_vib = st.selectbox("Sensor Vibração", tags_vib)

    with col2:
        st.markdown("### Especificações")
        nome = st.text_input("Nome do Ativo")
        modelo = st.selectbox(
            "Modelo",
            ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"]
        )
        carga = st.number_input("Carga Operacional (Kg)", min_value=0.0)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Registrar Novo Ativo"):
        if not nome:
            st.error("Informe o nome do ativo.")
            return

        payload = {
            "nome_identificacao": nome,
            "modelo": modelo,
            "carga_kg": carga,
            "tag_clp_vinculada": tag_clp,
            "id_sensor_vinculado": tag_vib,
            "estado_integridade": "ORIGINAL",
            "modo_aprendizado_concluido": False,
            "ciclos_acumulados": 0,
            "vida_util_nominal_ciclos": 10000000,
            "status": "NORMAL",
            "rul_percentual": 100,
            "data_registro": datetime.now(timezone.utc).isoformat()
        }
        registrar_cilindro(payload)
        st.success("Ativo registrado com sucesso.")

# =========================================================
# DIAGNÓSTICO
# =========================================================
def tela_diagnostico():
    hero_header()
    cilindros = buscar_cilindros()

    if not cilindros:
        st.warning("Nenhum ativo encontrado.")
        return

    mapa = {c['nome_identificacao']: c for c in cilindros}
    ativo_nome = st.selectbox("Selecionar Ativo", list(mapa.keys()))
    ativo = mapa[ativo_nome]
    id_doc = ativo['id_documento']
    rul = ativo.get('rul_percentual', 100)

    col1, col2 = st.columns([1,2])

    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rul,
            number={'suffix':'%', 'font':{'size':42, 'color':'white'}},
            gauge={
                'axis':{'range':[0,100]},
                'bar':{'color':'#3B82F6'},
                'bgcolor':'#0F172A',
                'steps':[
                    {'range':[0,20],'color':'#451A1A'},
                    {'range':[20,50],'color':'#78350F'},
                    {'range':[50,100],'color':'#0F172A'}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        c1, c2 = st.columns(2)
        c1.metric("Ciclos Acumulados", f"{ativo.get('ciclos_acumulados',0):,}".replace(",","."))
        c2.metric("Status", ativo.get('status','NORMAL'))
        c1.metric("Integridade", ativo.get('estado_integridade','ORIGINAL'))
        c2.metric("Tag CLP", ativo.get('tag_clp_vinculada','-'))

        st.markdown("### Intervenções")
        a1, a2, a3 = st.columns(3)

        with a1:
            if st.button("Recalibrar Baseline"):
                atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
                st.success("Baseline reiniciada.")

        with a2:
            tipo = st.selectbox("Manutenção", ["Reparo", "Substituição"])
            if st.button("Executar Manutenção"):
                if tipo == "Substituição":
                    atualizar_status_cilindro(
                        id_doc,
                        {
                            "estado_integridade":"ORIGINAL",
                            "ciclos_acumulados":0,
                            "rul_percentual":100,
                            "modo_aprendizado_concluido":False
                        }
                    )
                    st.success("Substituição concluída.")
                else:
                    atualizar_status_cilindro(id_doc, {"estado_integridade":"REPARADO"})
                    st.warning("Ativo marcado como reparado.")

        with a3:
            if st.button("Sinalizar Falha"):
                atualizar_status_cilindro(id_doc, {"status":"FALHA IMINENTE"})
                st.error("Falha crítica registrada.")

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-title">
            KOPEMPACK
        </div>
        <div class="sidebar-subtitle">
            OPERATIONS CENTER
        </div>
    </div>
    """, unsafe_allow_html=True)

    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Comissionamento", "Diagnóstico"],
        icons=["speedometer2", "cpu", "activity"],
        default_index=0,
        styles={
            "container":{
                "background-color":"#0B111C",
                "padding":"0!important"
            },
            "icon":{
                "color":"#3B82F6",
                "font-size":"18px"
            },
            "nav-link":{
                "font-size":"15px",
                "text-align":"left",
                "margin":"6px",
                "border-radius":"10px",
                "--hover-color":"#111827",
                "color":"white"
            },
            "nav-link-selected":{
                "background-color":"#2563EB"
            }
        }
    )

# =========================================================
# ROUTER
# =========================================================
if menu == "Dashboard":
    tela_dashboard()
elif menu == "Comissionamento":
    tela_comissionamento()
elif menu == "Diagnóstico":
    tela_diagnostico()
