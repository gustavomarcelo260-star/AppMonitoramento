import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Supervisório Kopempack",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. DESIGN DE INTERFACE (CSS AVANÇADO)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e Tipografia Global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Ocultar elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Estilização da Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0B0E14;
        border-right: 1px solid #1E2330;
    }
    
    /* Cards de Métricas Premium */
    div[data-testid="metric-container"] {
        background-color: #12161F;
        border: 1px solid #1E2330;
        padding: 24px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        border-top: 4px solid #3b82f6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
    }
    
    div[data-testid="metric-container"] label {
        color: #8B949E !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 2.4rem !important;
        font-weight: 700 !important;
        line-height: 1.2;
    }

    /* Estilização de Botões */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        border: 1px solid #2A3040 !important;
        background-color: #1A1D26 !important;
        color: #E2E8F0 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
        background-color: #1E2330 !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5) !important;
    }

    /* Títulos e Divisores */
    h1, h2, h3 {
        color: #F8FAFC !important;
        letter-spacing: -0.02em;
        font-weight: 600 !important;
    }
    
    hr {
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
        border: 0;
        border-top: 1px solid #1E2330;
    }
    
    /* Tabelas */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #1E2330;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CABEÇALHO E BRANDING
# ==========================================
try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("<h2 style='text-align: center; color: #fff;'>⚙️ KOPEMPACK</h2>", unsafe_allow_html=True)

st.sidebar.markdown("---")

# ==========================================
# 4. CONEXÃO COM BANCO DE DADOS
# ==========================================
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            cert = dict(st.secrets["firebase"])
            cert["private_key"] = cert["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cert)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.sidebar.error("Desconectado do Banco de Dados.")
        return None

db = init_firebase()

def buscar_cilindros():
    if not db: return []
    try:
        docs = db.collection('cilindros_ativos').stream()
        return [{"id_documento": doc.id, **doc.to_dict()} for doc in docs]
    except Exception:
        return []

def registrar_cilindro(payload):
    if db: db.collection('cilindros_ativos').add(payload)

def atualizar_status_cilindro(id_documento, campos_atualizados):
    if db: db.collection('cilindros_ativos').document(id_documento).update(campos_atualizados)

# ==========================================
# 5. MÓDULOS DA APLICAÇÃO
# ==========================================
def tela_visao_geral():
    st.title("Visão Geral da Planta")
    st.markdown("<p style='color: #8B949E;'>Monitoramento em tempo real dos ativos pneumáticos e indicadores de saúde.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    cilindros = buscar_cilindros()
    
    if not cilindros:
        st.info("Nenhum cilindro cadastrado no banco de dados. Acesse 'Comissionamento' no menu lateral para registrar o primeiro ativo.")
        return

    df = pd.DataFrame(cilindros)
    
    # Padronização de dados ausentes para evitar erros de renderização
    if 'status' not in df.columns: df['status'] = "NORMAL"
    if 'rul_percentual' not in df.columns: df['rul_percentual'] = 100

    total = len(df)
    em_atencao = len(df[df['status'] == 'ATENÇÃO'])
    em_falha = len(df[df['status'] == 'FALHA IMINENTE'])
    
    # Layout de Métricas com espaçamento otimizado
    col1, col2, col3 = st.columns(3, gap="large")
    col1.metric("Ativos Monitorados", total)
    col2.metric("Alertas de Atenção", em_atencao)
    col3.metric("Falhas Críticas", em_falha)
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.subheader("Status Operacional dos Equipamentos")
    
    colunas_exibicao = ['nome_identificacao', 'tag_clp_vinculada', 'estado_integridade', 'rul_percentual', 'status']
    colunas_presentes = [col for col in colunas_exibicao if col in df.columns]
    
    df_exibicao = df[colunas_presentes].copy()
    df_exibicao.columns = ['Identificação', 'Tag CLP', 'Integridade', 'RUL (%)', 'Status']
    
    # Renderização da Tabela Otimizada
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

def tela_comissionamento():
    st.title("Comissionamento de Hardware")
    st.markdown("<p style='color: #8B949E;'>Identificação e vínculo de dispositivos recém-descobertos na rede industrial.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    tags_clp_disponiveis = ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04", "SIM_CLP_05"]
    tags_vib_disponiveis = ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04", "SIM_VIB_05"]
    
    # Estruturação em containers simulando "Cards"
    with st.container():
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown("#### Parâmetros de Rede e Integração")
            tag_clp = st.selectbox("Tag CLP Detectada (Leitura QR):", tags_clp_disponiveis)
            tag_vib = st.selectbox("ID Sensor Vibração Detectado:", tags_vib_disponiveis)
            
        with col2:
            st.markdown("#### Especificações do Equipamento")
            nome_identificacao = st.text_input("Nome/Posição na Máquina", placeholder="Ex: Empurrador Estação 1")
            modelo_cilindro = st.selectbox("Modelo do Fabricante", ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"])
            peso_carga = st.number_input("Carga de Trabalho (Kg)", min_value=0.0, step=1.0)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botão primário estilizado para ações afirmativas
    if st.button("Registrar Novo Ativo", type="primary"):
        if not nome_identificacao:
            st.error("O campo 'Nome/Posição na Máquina' é obrigatório.")
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
        st.toast(f"Ativo '{nome_identificacao}' registrado com sucesso na base de dados.", icon="✅")

def tela_diagnostico():
    st.title("Diagnóstico e Intervenção")
    st.markdown("<p style='color: #8B949E;'>Análise técnica individualizada e registro em diário de manutenção.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    cilindros = buscar_cilindros()
    if not cilindros:
        st.warning("A base de dados de ativos está vazia. Não é possível realizar diagnósticos.")
        return
        
    opcoes_cilindros = {c['nome_identificacao']: c for c in cilindros}
    selecao = st.sidebar.selectbox("Selecione o Ativo para Análise:", list(opcoes_cilindros.keys()))
    
    ativo_atual = opcoes_cilindros[selecao]
    id_doc = ativo_atual['id_documento']
    
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    col1.metric("Vida Útil Restante", f"{ativo_atual.get('rul_percentual', 100)}%")
    col2.metric("Ciclos Acumulados", f"{ativo_atual.get('ciclos_acumulados', 0):,}".replace(",", "."))
    col3.metric("Status Sistêmico", ativo_atual.get('status', 'NORMAL'))
    col4.metric("Integridade Física", ativo_atual.get('estado_integridade', 'ORIGINAL'))
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.subheader("Controle de Intervenções de Manutenção")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_acao1, col_acao2, col_acao3 = st.columns(3, gap="large")
    
    with col_acao1:
        st.markdown("**Recalibração do Ativo**")
        if st.button("Forçar Nova Baseline", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
            st.toast("Baseline invalidada. Novo ciclo de aprendizado iniciado.", icon="🔄")
            
    with col_acao2:
        st.markdown("**Registro de Ação Corretiva**")
        tipo_intervencao = st.selectbox("Selecione o procedimento executado", ["Manutenção (Reparo)", "Troca Integral (Substituição)"], label_visibility="collapsed")
        if st.button("Gravar Intervenção", use_container_width=True):
            if "Troca" in tipo_intervencao:
                atualizar_status_cilindro(id_doc, {
                    "estado_integridade": "ORIGINAL",
                    "ciclos_acumulados": 0,
                    "rul_percentual": 100,
                    "modo_aprendizado_concluido": False
                })
                st.toast("Substituição registrada. Histórico logístico e RUL foram zerados.", icon="✅")
            else:
                atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                st.toast("Status atualizado para REPARADO.", icon="⚠️")
                
    with col_acao3:
        st.markdown("**Registro de Falhas**")
        if st.button("Sinalizar Falha/Quebra", type="primary", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"status": "FALHA CRÍTICA"})
            st.error("Falha Crítica registrada no banco de dados e repassada ao CLP.")

# ==========================================
# 6. ROTEAMENTO
# ==========================================
st.sidebar.markdown("<br>", unsafe_allow_html=True)
menu = st.sidebar.radio(
    "Navegação do Sistema:", 
    ["📊 Visão Geral da Planta", "⚙️ Comissionamento", "🔍 Diagnóstico e Intervenção"]
)

if menu == "📊 Visão Geral da Planta":
    tela_visao_geral()
elif menu == "⚙️ Comissionamento":
    tela_comissionamento()
elif menu == "🔍 Diagnóstico e Intervenção":
    tela_diagnostico()
