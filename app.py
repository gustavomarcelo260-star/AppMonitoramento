import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema Supervisório - Kopempack",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. DESIGN DE INTERFACE CORPORATIVO
# ==========================================
st.markdown("""
    <style>
    /* Correção do Menu e Header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent !important;}
    
    /* Tipografia e Fundo Geral */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #091120;
    }
    
    [data-testid="stSidebar"] {
        background-color: #050914 !important;
        border-right: 1px solid #162238;
    }
    
    /* Cards de Métricas */
    div[data-testid="metric-container"] {
        background-color: #111A2F;
        border: 1px solid #1E2B45;
        padding: 20px;
        border-radius: 4px;
        border-top: 3px solid #2563EB;
    }
    
    div[data-testid="metric-container"] label {
        color: #8BA0B8 !important;
        font-size: 0.80rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 2rem !important;
        font-weight: 300 !important;
    }

    /* Botões */
    .stButton > button {
        border-radius: 4px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        border: 1px solid #1E2B45 !important;
        background-color: #111A2F !important;
        color: #E2E8F0 !important;
    }
    
    .stButton > button:hover {
        border-color: #2563EB !important;
        color: #FFFFFF !important;
        background-color: #162238 !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        border: none !important;
        color: white !important;
    }
    
    /* Títulos e Linhas */
    h1, h2, h3, h4 {
        color: #FFFFFF !important;
        font-weight: 400 !important;
    }
    
    hr {
        border: 0;
        border-top: 1px solid #1E2B45;
        margin: 1.5rem 0;
    }
    
    /* Tabelas e Inputs */
    [data-testid="stDataFrame"] {
        border: 1px solid #1E2B45;
        border-radius: 4px;
    }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #111A2F !important;
        border: 1px solid #1E2B45 !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# Sistema Supervisório Central")

try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("<h2 style='text-align: center; color: #fff; font-weight: 600;'>KOPEMPACK</h2>", unsafe_allow_html=True)

st.sidebar.markdown("---")

# ==========================================
# 3. INICIALIZAÇÃO DO FIREBASE
# ==========================================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cert = dict(st.secrets["firebase"])
        cert["private_key"] = cert["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ==========================================
# 4. FUNÇÕES DE BANCO DE DADOS
# ==========================================
def buscar_cilindros():
    docs = db.collection('cilindros_ativos').stream()
    lista_cilindros = []
    for doc in docs:
        dado = doc.to_dict()
        dado['id_documento'] = doc.id
        lista_cilindros.append(dado)
    return lista_cilindros

def registrar_cilindro(payload):
    db.collection('cilindros_ativos').add(payload)

def atualizar_status_cilindro(id_documento, campos_atualizados):
    db.collection('cilindros_ativos').document(id_documento).update(campos_atualizados)

# ==========================================
# 5. TELAS DO APLICATIVO
# ==========================================
def tela_visao_geral():
    st.markdown("### Dashboard da Planta")
    st.markdown("<p style='color: #8BA0B8; font-size: 0.9rem;'>Monitoramento e telemetria em tempo real dos ativos pneumáticos.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    cilindros = buscar_cilindros()
    
    if not cilindros:
        st.info("Nenhum ativo cadastrado na base de dados.")
        return

    df = pd.DataFrame(cilindros)
    total = len(df)
    
    if 'status' not in df.columns: df['status'] = "NORMAL"
    if 'rul_percentual' not in df.columns: df['rul_percentual'] = 100

    em_atencao = len(df[df['status'] == 'ATENÇÃO'])
    em_falha = len(df[df['status'] == 'FALHA IMINENTE'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ativos Operacionais", total)
    col2.metric("Alertas de Monitoramento", em_atencao)
    col3.metric("Ocorrências Críticas", em_falha)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    col_grafico1, col_grafico2 = st.columns(2)
    
    with col_grafico1:
        st.markdown("<h4 style='font-size: 1rem;'>Status Operacional</h4>", unsafe_allow_html=True)
        fig_status = px.pie(
            df, 
            names='status', 
            hole=0.7,
            color='status',
            color_discrete_map={
                'NORMAL': '#2563EB',
                'ATENÇÃO': '#F59E0B',
                'FALHA IMINENTE': '#EF4444'
            }
        )
        fig_status.update_traces(textposition='outside', textinfo='percent+label', marker=dict(line=dict(color='#091120', width=3)))
        fig_status.update_layout(
            height=280,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFFFFF'),
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_grafico2:
        st.markdown("<h4 style='font-size: 1rem;'>Health Score (RUL %)</h4>", unsafe_allow_html=True)
        df_sorted = df.sort_values(by='rul_percentual', ascending=True)
        fig_rul = px.bar(
            df_sorted, 
            x='rul_percentual', 
            y='nome_identificacao', 
            orientation='h',
            color='rul_percentual',
            color_continuous_scale=['#EF4444', '#F59E0B', '#2563EB'],
            range_color=[0, 100]
        )
        fig_rul.update_layout(
            height=280,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFFFFF'),
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(title="", gridcolor="#1E2B45", showline=False),
            yaxis=dict(title="", showgrid=False),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_rul, use_container_width=True)
    
    st.markdown("<br><h4 style='font-size: 1.1rem;'>Tabela de Ativos em Tempo Real</h4>", unsafe_allow_html=True)
    colunas_exibicao = ['nome_identificacao', 'tag_clp_vinculada', 'estado_integridade', 'rul_percentual', 'status']
    colunas_presentes = [col for col in colunas_exibicao if col in df.columns]
    
    df_exibicao = df[colunas_presentes].copy()
    df_exibicao.columns = ['Identificação', 'Tag CLP', 'Integridade', 'RUL (%)', 'Status']
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

def tela_comissionamento():
    st.markdown("### Comissionamento de Hardware")
    st.markdown("<p style='color: #8BA0B8; font-size: 0.9rem;'>Registro de integração de novos dispositivos industriais.</p>", unsafe_allow_html=True)
    st.divider()
    
    tags_clp_disponiveis = ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04", "SIM_CLP_05"]
    tags_vib_disponiveis = ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04", "SIM_VIB_05"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='font-size: 1rem;'>Vínculo Lógico</h4>", unsafe_allow_html=True)
        tag_clp = st.selectbox("Tag CLP Detectada:", tags_clp_disponiveis)
        tag_vib = st.selectbox("ID Sensor de Vibração:", tags_vib_disponiveis)
        
    with col2:
        st.markdown("<h4 style='font-size: 1rem;'>Especificações Mecânicas</h4>", unsafe_allow_html=True)
        nome_identificacao = st.text_input("Nomenclatura do Ativo", placeholder="Ex: Cilindro Estação 1")
        modelo_cilindro = st.selectbox("Família / Modelo", ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"])
        peso_carga = st.number_input("Carga Operacional (Kg)", min_value=0.0, step=1.0)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Registrar Comissionamento", type="primary"):
        if not nome_identificacao:
            st.error("A nomenclatura do ativo é obrigatória.")
            return
            
        payload = {
            "nome_identificacao": nome_identificacao,
            "modelo": modelo_cilindro,
            "carga_kg": peso_carga,
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
        st.success(f"Ativo '{nome_identificacao}' sincronizado com sucesso no banco de dados.")

def tela_diagnostico():
    st.markdown("### Diagnóstico Especializado")
    st.markdown("<p style='color: #8BA0B8; font-size: 0.9rem;'>Análise de integridade e registro de manutenções corretivas.</p>", unsafe_allow_html=True)
    st.divider()
    
    cilindros = buscar_cilindros()
    if not cilindros:
        st.warning("Base de dados vazia.")
        return
        
    opcoes_cilindros = {c['nome_identificacao']: c for c in cilindros}
    selecao = st.sidebar.selectbox("Filtro de Ativo:", list(opcoes_cilindros.keys()))
    
    ativo_atual = opcoes_cilindros[selecao]
    id_doc = ativo_atual['id_documento']
    rul_atual = ativo_atual.get('rul_percentual', 100)
    
    col_gauge, col_kpis = st.columns([1, 2])
    
    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = rul_atual,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Health Score", 'font': {'color': '#8BA0B8', 'size': 14}},
            number = {'suffix': "%", 'font': {'color': '#FFFFFF', 'size': 36}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#1E2B45", 'visible': False},
                'bar': {'color': "#2563EB" if rul_atual > 50 else ("#F59E0B" if rul_atual > 20 else "#EF4444"), 'thickness': 0.6},
                'bgcolor': "#111A2F",
                'borderwidth': 0,
                'steps': [
                    {'range': [0, 20], 'color': 'rgba(239, 68, 68, 0.1)'},
                    {'range': [20, 50], 'color': 'rgba(245, 158, 11, 0.1)'},
                    {'range': [50, 100], 'color': 'rgba(37, 99, 235, 0.1)'}],
            }
        ))
        fig_gauge.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=250,
            margin=dict(t=30, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_kpis:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.metric("Ciclos Acumulados", f"{ativo_atual.get('ciclos_acumulados', 0):,}".replace(",", "."))
        col2.metric("Status Sistêmico", ativo_atual.get('status', 'NORMAL'))
        col1.metric("Condição Física", ativo_atual.get('estado_integridade', 'ORIGINAL'))
        col2.metric("Endereço de Rede", ativo_atual.get('tag_clp_vinculada', '-'))
    
    st.divider()
    st.markdown("<h4 style='font-size: 1rem;'>Painel de Intervenções</h4><br>", unsafe_allow_html=True)
    
    col_acao1, col_acao2, col_acao3 = st.columns(3)
    
    with col_acao1:
        st.markdown("<span style='font-size: 0.9rem; font-weight: 600; color: #8BA0B8;'>CALIBRAÇÃO</span>", unsafe_allow_html=True)
        if st.button("Forçar Nova Baseline", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
            st.success("Baseline invalidada. Reiniciando ciclo de aprendizado.")
            
    with col_acao2:
        st.markdown("<span style='font-size: 0.9rem; font-weight: 600; color: #8BA0B8;'>MANUTENÇÃO</span>", unsafe_allow_html=True)
        tipo_intervencao = st.selectbox("Selecione a Ação", ["Manutenção (Reparo)", "Troca Integral (Substituição)"], label_visibility="collapsed")
        if st.button("Registrar Ordem", use_container_width=True):
            if "Troca" in tipo_intervencao:
                atualizar_status_cilindro(id_doc, {
                    "estado_integridade": "ORIGINAL",
                    "ciclos_acumulados": 0,
                    "rul_percentual": 100,
                    "modo_aprendizado_concluido": False
                })
                st.success("Substituição computada. Logística resetada.")
            else:
                atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                st.warning("Sinalizado como REPARADO.")
                
    with col_acao3:
        st.markdown("<span style='font-size: 0.9rem; font-weight: 600; color: #8BA0B8;'>EMERGÊNCIA</span>", unsafe_allow_html=True)
        if st.button("Sinalizar Falha Crítica", type="primary", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"status": "FALHA IMINENTE"})
            st.error("Ocorrência crítica registrada.")

# ==========================================
# 6. ROTEAMENTO DE NAVEGAÇÃO LATERAL
# ==========================================
st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #8BA0B8; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;'>MÓDULOS</p>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "", 
    ["Dashboard da Planta", "Comissionamento", "Diagnóstico Especializado"],
    label_visibility="collapsed"
)

if menu == "Dashboard da Planta":
    tela_visao_geral()
elif menu == "Comissionamento":
    tela_comissionamento()
elif menu == "Diagnóstico Especializado":
    tela_diagnostico()
