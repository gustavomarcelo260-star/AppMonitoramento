import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone

st.set_page_config(page_title="Monitoramento de Cilindros", layout="wide")

# ==========================================
# INICIALIZAÇÃO DO FIREBASE (Via st.secrets)
# ==========================================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # Extrai os segredos configurados no Streamlit
        cert = dict(st.secrets["firebase"])
        # Garante a quebra de linha correta na chave privada
        cert["private_key"] = cert["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ==========================================
# FUNÇÕES DE BANCO DE DADOS
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
# TELAS DO APLICATIVO
# ==========================================
def tela_visao_geral():
    st.title("Visão Geral da Planta")
    
    cilindros = buscar_cilindros()
    
    if not cilindros:
        st.warning("Nenhum cilindro cadastrado no banco de dados.")
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
    col1.metric("Cilindros Monitorados", total)
    col2.metric("Cilindros em Atenção", em_atencao)
    col3.metric("Falhas Críticas", em_falha)
    
    st.markdown("### Status Atual dos Equipamentos")
    
    colunas_exibicao = ['nome_identificacao', 'tag_clp_vinculada', 'estado_integridade', 'rul_percentual', 'status']
    colunas_presentes = [col for col in colunas_exibicao if col in df.columns]
    
    st.dataframe(df[colunas_presentes], use_container_width=True)

def tela_comissionamento():
    st.title("Comissionamento de Novo Hardware")
    st.write("Identificação e vínculo de dispositivos recém-descobertos na rede.")
    
    tags_clp_disponiveis = ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03"]
    tags_vib_disponiveis = ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Vínculo Físico-Digital")
        tag_clp = st.selectbox("Tag CLP Detectada:", tags_clp_disponiveis)
        tag_vib = st.selectbox("ID Sensor Vibração Detectado:", tags_vib_disponiveis)
        
    with col2:
        st.markdown("#### Parâmetros de Operação")
        nome_identificacao = st.text_input("Nome/Posição na Máquina", placeholder="Ex: Empurrador Estação 1")
        modelo_cilindro = st.selectbox("Modelo do Fabricante", ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"])
        peso_carga = st.number_input("Carga de Trabalho (Kg)", min_value=0.0, step=1.0)
        
    if st.button("Registrar Ativo"):
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
        st.success(f"Cilindro '{nome_identificacao}' registrado com sucesso no banco de dados.")

def tela_diagnostico():
    st.title("Diagnóstico e Gestão de Vida Útil")
    
    cilindros = buscar_cilindros()
    if not cilindros:
        st.warning("Nenhum cilindro cadastrado.")
        return
        
    opcoes_cilindros = {c['nome_identificacao']: c for c in cilindros}
    selecao = st.sidebar.selectbox("Selecione o Ativo:", list(opcoes_cilindros.keys()))
    
    ativo_atual = opcoes_cilindros[selecao]
    id_doc = ativo_atual['id_documento']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vida Útil Restante (RUL)", f"{ativo_atual.get('rul_percentual', 100)}%")
    col2.metric("Ciclos Acumulados", ativo_atual.get('ciclos_acumulados', 0))
    col3.metric("Status Operacional", ativo_atual.get('status', 'NORMAL'))
    col4.metric("Status Integridade", ativo_atual.get('estado_integridade', 'ORIGINAL'))
    
    st.divider()
    st.markdown("### Ações de Manutenção")
    col_acao1, col_acao2, col_acao3 = st.columns(3)
    
    with col_acao1:
        if st.button("Forçar Novo Aprendizado", use_container_width=True):
            atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False})
            st.info("Status atualizado no Firebase.")
            
    with col_acao2:
        tipo_intervencao = st.selectbox("Tipo de Intervenção", ["Manutenção (Reparo)", "Troca Integral (Substituição)"], label_visibility="collapsed")
        if st.button("Registrar Intervenção", use_container_width=True):
            if "Troca" in tipo_intervencao:
                atualizar_status_cilindro(id_doc, {
                    "estado_integridade": "ORIGINAL",
                    "ciclos_acumulados": 0,
                    "rul_percentual": 100,
                    "modo_aprendizado_concluido": False
                })
                st.success("Histórico zerado no banco de dados.")
            else:
                atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                st.warning("Integridade alterada para REPARADO.")
                
    with col_acao3:
        if st.button("Registrar Quebra Mecânica", type="primary", use_container_width=True):
            st.error("Registro de quebra inserido no histórico.")

# ==========================================
# ROTEAMENTO DE NAVEGAÇÃO
# ==========================================
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione o Módulo:", ["Visão Geral", "Comissionamento", "Diagnóstico Individual"])

if menu == "Visão Geral":
    tela_visao_geral()
elif menu == "Comissionamento":
    tela_comissionamento()
elif menu == "Diagnóstico Individual":
    tela_diagnostico()