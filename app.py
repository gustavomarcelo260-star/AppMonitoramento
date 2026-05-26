import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timezone

# 1. CONFIGURAÇÃO DA PÁGINA E TÍTULO DO APP
st.set_page_config(
    page_title="Sistema Supervisório - Kopempack",
    page_icon="⚙️",
    layout="wide"
)

# 2. ESTILO E LOGOTIPO
def aplicar_branding():
    # Título Principal na Tela
    st.title("Sistema Supervisório - Kopempack")
    
    # Logotipo na Sidebar (Utilizando um ícone industrial como fallback)
    # Dica: Substitua 'logo.png' pelo caminho do seu arquivo local
    try:
        st.sidebar.image("logo.png", width=200)
    except:
        st.sidebar.markdown("## ⚙️ **KOPEMPACK**")
        st.sidebar.markdown("---")
        
# 2. INJEÇÃO DE CSS CUSTOMIZADO (Design de Interface)
def aplicar_estilo_ui():
    st.markdown("""
        <style>
        /* Oculta os elementos padrão do Streamlit para aspecto de software standalone */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Estilização dos Cards de KPI (st.metric) */
        div[data-testid="metric-container"] {
            background-color: #1A1C24;
            border: 1px solid #2A2D3D;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            border-left: 4px solid #3b82f6;
        }
        
        /* Títulos e espaçamentos */
        h1, h2, h3 {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 600;
        }
        
        /* Linhas divisórias personalizadas */
        hr {
            margin-top: 1rem;
            margin-bottom: 2rem;
            border: 0;
            border-top: 1px solid #2A2D3D;
        }
        </style>
    """, unsafe_allow_html=True)

aplicar_estilo_ui()

# 3. INICIALIZAÇÃO DO FIREBASE
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cert = dict(st.secrets["firebase"])
        cert["private_key"] = cert["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# 4. FUNÇÕES DE BANCO DE DADOS
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

# 5. TELAS DO APLICATIVO
def tela_visao_geral():
    st.title("📊 Visão Geral da Planta")
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
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ativos Monitorados", total)
    col2.metric("Alertas de Atenção", em_atencao)
    col3.metric("Falhas Críticas", em_falha)
    
    st.markdown("<br><h3>Status Atual dos Equipamentos</h3>", unsafe_allow_html=True)
    
    colunas_exibicao = ['nome_identificacao', 'tag_clp_vinculada', 'estado_integridade', 'rul_percentual', 'status']
    colunas_presentes = [col for col in colunas_exibicao if col in df.columns]
    
    df_exibicao = df[colunas_presentes].copy()
    df_exibicao.columns = ['Identificação', 'Tag CLP', 'Integridade', 'RUL (%)', 'Status']
    
    # Exibe a tabela ocultando o índice numérico padrão do Pandas
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

def tela_comissionamento():
    st.title("⚙️ Comissionamento de Novo Hardware")
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
        st.success(f"Ativo '{nome_identificacao}' registrado com sucesso. Iniciando em Modo de Aprendizado.")

def tela_diagnostico():
    st.title("🔍 Diagnóstico e Gestão de Vida Útil")
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
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vida Útil Restante (RUL)", f"{ativo_atual.get('rul_percentual', 100)}%")
    col2.metric("Ciclos Acumulados", ativo_atual.get('ciclos_acumulados', 0))
    col3.metric("Status Operacional", ativo_atual.get('status', 'NORMAL'))
    col4.metric("Status Integridade", ativo_atual.get('estado_integridade', 'ORIGINAL'))
    
    st.divider()
    st.markdown("### Ações de Intervenção de Manutenção")
    st.markdown("Execute comandos para atualizar a lógica de cálculo após intervenções físicas.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_acao1, col_acao2, col_acao3 = st.columns(3)
    
    with col_acao1:
        if st.button("Forçar Recalibragem de Tempos", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
            st.info("Baseline invalidada. Aguardando novos ciclos para recálculo.")
            
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
                st.success("Histórico logístico zerado. Ativo operando como novo.")
            else:
                atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                st.warning("Status de integridade rebaixado para REPARADO.")
                
    with col_acao3:
        if st.button("Registrar Falha Crítica / Quebra", type="primary", use_container_width=True):
            st.error("Falha registrada. O MTBF contextual deste local será recalculado.")

# 6. ROTEAMENTO DE NAVEGAÇÃO LATERAL
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/2f/Logo_SENAI.svg", width=150)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "MENU DE OPERAÇÃO:", 
    ["📊 Visão Geral", "⚙️ Comissionamento", "🔍 Diagnóstico Individual"]
)

if menu == "📊 Visão Geral":
    tela_visao_geral()
elif menu == "⚙️ Comissionamento":
    tela_comissionamento()
elif menu == "🔍 Diagnóstico Individual":
    tela_diagnostico()
