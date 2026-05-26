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
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. DESIGN DE INTERFACE (CSS) E BRANDING
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    div[data-testid="metric-container"] {
        background-color: #1A1C24;
        border: 1px solid #2A2D3D;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border-left: 4px solid #DEFF9A;
    }
    
    h1, h2, h3 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 600;
    }
    
    hr {
        margin-top: 1rem;
        margin-bottom: 2rem;
        border: 0;
        border-top: 1px solid #2A2D3D;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# ⚙️ Sistema Supervisório - Kopempack")

try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("## ⚙️ **KOPEMPACK**")

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
    st.subheader("📊 Visão Geral da Planta")
    st.markdown("Monitoramento em tempo real dos ativos pneumáticos.")
    st.divider()
    
    cilindros = buscar_cilindros()
    
    if not cilindros:
        st.info("Nenhum cilindro cadastrado no banco de dados. Acesse 'Comissionamento' para registrar o primeiro ativo.")
        return

    df = pd.DataFrame(cilindros)
    total = len(df)
    
    if 'status' not in df.columns:
        df['status'] = "NORMAL"
    if 'rul_percentual' not in df.columns:
        df['rul_percentual'] = 100

    em_atencao = len(df[df['status'] == 'ATENÇÃO'])
    em_falha = len(df[df['status'] == 'FALHA IMINENTE'])
    
    # KPIs Topo
    col1, col2, col3 = st.columns(3)
    col1.metric("Ativos Monitorados", total)
    col2.metric("Alertas de Atenção", em_atencao)
    col3.metric("Falhas Críticas", em_falha)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Sessão de Gráficos Analíticos
    col_grafico1, col_grafico2 = st.columns(2)
    
    with col_grafico1:
        st.markdown("#### Distribuição de Status Operacional")
        # Gráfico de Rosca
        fig_status = px.pie(
            df, 
            names='status', 
            hole=0.6,
            color='status',
            color_discrete_map={
                'NORMAL': '#DEFF9A',
                'ATENÇÃO': '#F59E0B',
                'FALHA IMINENTE': '#EF4444'
            }
        )
        fig_status.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_grafico2:
        st.markdown("#### Vida Útil Restante (RUL %)")
        # Gráfico de Barras
        df_sorted = df.sort_values(by='rul_percentual', ascending=True)
        fig_rul = px.bar(
            df_sorted, 
            x='rul_percentual', 
            y='nome_identificacao', 
            orientation='h',
            color='rul_percentual',
            color_continuous_scale=['#EF4444', '#F59E0B', '#DEFF9A'],
            range_color=[0, 100]
        )
        fig_rul.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            margin=dict(t=20, b=20, l=20, r=20),
            xaxis_title="RUL (%)",
            yaxis_title=""
        )
        st.plotly_chart(fig_rul, use_container_width=True)
    
    st.divider()
    st.markdown("### Tabela de Ativos")
    
    colunas_exibicao = ['nome_identificacao', 'tag_clp_vinculada', 'estado_integridade', 'rul_percentual', 'status']
    colunas_presentes = [col for col in colunas_exibicao if col in df.columns]
    
    df_exibicao = df[colunas_presentes].copy()
    df_exibicao.columns = ['Identificação', 'Tag CLP', 'Integridade', 'RUL (%)', 'Status']
    
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

def tela_comissionamento():
    st.subheader("⚙️ Comissionamento de Novo Hardware")
    st.markdown("Identificação e vínculo de dispositivos recém-descobertos na rede industrial.")
    st.divider()
    
    tags_clp_disponiveis = ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04", "SIM_CLP_05"]
    tags_vib_disponiveis = ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04", "SIM_VIB_05"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Vínculo Físico-Digital")
        tag_clp = st.selectbox("Tag CLP Detectada (Leitura QR):", tags_clp_disponiveis)
        tag_vib = st.selectbox("ID Sensor Vibração Detectado:", tags_vib_disponiveis)
        
    with col2:
        st.markdown("#### Parâmetros de Operação")
        nome_identificacao = st.text_input("Nome/Posição na Máquina", placeholder="Ex: Empurrador Estação 1")
        modelo_cilindro = st.selectbox("Modelo do Fabricante", ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"])
        peso_carga = st.number_input("Carga de Trabalho (Kg)", min_value=0.0, step=1.0)
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Registrar Ativo no Banco de Dados", type="primary"):
        if not nome_identificacao:
            st.error("O nome de identificação é obrigatório.")
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
        st.success(f"Ativo '{nome_identificacao}' registrado com sucesso.")

def tela_diagnostico():
    st.subheader("🔍 Diagnóstico e Gestão de Vida Útil")
    st.markdown("Análise técnica individual e registro de intervenções.")
    st.divider()
    
    cilindros = buscar_cilindros()
    if not cilindros:
        st.warning("Nenhum cilindro cadastrado para diagnóstico.")
        return
        
    opcoes_cilindros = {c['nome_identificacao']: c for c in cilindros}
    selecao = st.sidebar.selectbox("Selecione o Ativo para Análise:", list(opcoes_cilindros.keys()))
    
    ativo_atual = opcoes_cilindros[selecao]
    id_doc = ativo_atual['id_documento']
    rul_atual = ativo_atual.get('rul_percentual', 100)
    
    col_gauge, col_kpis = st.columns([1, 2])
    
    with col_gauge:
        # Gráfico de Velocímetro (Gauge) para o RUL
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = rul_atual,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Saúde do Ativo (%)", 'font': {'color': '#FAFAFA'}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#DEFF9A" if rul_atual > 50 else ("#F59E0B" if rul_atual > 20 else "#EF4444")},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#333",
                'steps': [
                    {'range': [0, 20], 'color': 'rgba(239, 68, 68, 0.3)'},
                    {'range': [20, 50], 'color': 'rgba(245, 158, 11, 0.3)'},
                    {'range': [50, 100], 'color': 'rgba(222, 255, 154, 0.2)'}],
            }
        ))
        fig_gauge.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            height=300,
            margin=dict(t=40, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_kpis:
        col1, col2 = st.columns(2)
        col1.metric("Ciclos Acumulados", ativo_atual.get('ciclos_acumulados', 0))
        col2.metric("Status Operacional", ativo_atual.get('status', 'NORMAL'))
        col1.metric("Status Integridade", ativo_atual.get('estado_integridade', 'ORIGINAL'))
        col2.metric("Tag de Campo", ativo_atual.get('tag_clp_vinculada', '-'))
    
    st.divider()
    st.markdown("### Ações de Intervenção de Manutenção")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_acao1, col_acao2, col_acao3 = st.columns(3)
    
    with col_acao1:
        if st.button("Forçar Recalibragem de Tempos", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
            st.info("Baseline invalidada.")
            
    with col_acao2:
        tipo_intervencao = st.selectbox("Tipo de Intervenção", ["Manutenção (Reparo)", "Troca Integral (Substituição)"], label_visibility="collapsed")
        if st.button("Gravar Intervenção", use_container_width=True):
            if "Troca" in tipo_intervencao:
                atualizar_status_cilindro(id_doc, {
                    "estado_integridade": "ORIGINAL",
                    "ciclos_acumulados": 0,
                    "rul_percentual": 100,
                    "modo_aprendizado_concluido": False
                })
                st.success("Histórico logístico zerado.")
            else:
                atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                st.warning("Status alterado para REPARADO.")
                
    with col_acao3:
        if st.button("Registrar Falha Crítica / Quebra", type="primary", use_container_width=True):
            st.error("Falha registrada.")

# ==========================================
# 6. ROTEAMENTO DE NAVEGAÇÃO LATERAL
# ==========================================
st.sidebar.markdown("### MENU DE OPERAÇÃO")
menu = st.sidebar.radio(
    "Selecione o módulo:", 
    ["📊 Visão Geral", "⚙️ Comissionamento", "🔍 Diagnóstico Individual"],
    label_visibility="collapsed"
)

if menu == "📊 Visão Geral":
    tela_visao_geral()
elif menu == "⚙️ Comissionamento":
    tela_comissionamento()
elif menu == "🔍 Diagnóstico Individual":
    tela_diagnostico()
