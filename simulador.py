import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import time
from datetime import datetime, timezone

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(page_title="Simulador Industrial Kopempack", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #070B14; color: white; }
    .stButton > button { background: #2563EB !important; color: white !important; border: none !important; }
    .control-panel { background: #0B111C; padding: 20px; border-radius: 12px; border: 1px solid #182234; margin-bottom: 10px; }
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
# FUNÇÕES DE INFRAESTRUTURA
# =========================================================
def inicializar_planta():
    ativos_padrao = [
        {"nome": "Cilindro Linha A-01", "clp": "SIM_CLP_01", "vib": "SIM_VIB_01"},
        {"nome": "Cilindro Selagem B-04", "clp": "SIM_CLP_02", "vib": "SIM_VIB_02"},
        {"nome": "Cilindro Rotativo C-07", "clp": "SIM_CLP_03", "vib": "SIM_VIB_03"}
    ]
    for ativo in ativos_padrao:
        db.collection('cilindros_ativos').add({
            "nome_identificacao": ativo['nome'],
            "tag_clp_vinculada": ativo['clp'],
            "id_sensor_vinculado": ativo['vib'],
            "estado_integridade": "ORIGINAL",
            "ciclos_acumulados": 0,
            "rul_percentual": 100,
            "status": "NORMAL"
        })
    st.success("Planta virtual inicializada com 3 ativos padrão.")
    st.rerun()

# =========================================================
# LÓGICA DE SIMULAÇÃO
# =========================================================
st.title("⚙️ Simulador de Processos Industrial")

ativos = list(db.collection('cilindros_ativos').stream())
if not ativos:
    st.warning("Nenhum ativo detectado na nuvem.")
    if st.button("Inicializar Planta Virtual (Bootstrapping)"):
        inicializar_planta()
    st.stop()

# Se houver ativos, segue o fluxo normal
ativos_data = [{'id_documento': a.id, **a.to_dict()} for a in ativos]

if 'running' not in st.session_state: st.session_state.running = False

c_btn1, c_btn2 = st.columns([1, 10])
if c_btn1.button("▶️ RUN"): st.session_state.running = True
if c_btn1.button("⏹️ STOP"): st.session_state.running = False

st.markdown("---")

for ativo in ativos_data:
    with st.container():
        st.markdown(f'<div class="control-panel">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.subheader(f"Ativo: {ativo['nome_identificacao']}")
        vib = col2.slider(f"Vibração (mm/s)", 1.0, 10.0, 2.0, key=f"vib_{ativo['id_documento']}")
        atraso = col3.slider(f"Atraso Ciclo (ms)", 0, 500, 0, key=f"atraso_{ativo['id_documento']}")
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.running:
    for ativo in ativos_data:
        # Lógica de ciclo
        atraso = st.session_state[f"atraso_{ativo['id_documento']}"]
        ciclos_novos = ativo.get('ciclos_acumulados', 0) + 1
        
        # Atualização no Firebase
        db.collection('cilindros_ativos').document(ativo['id_documento']).update({
            "ciclos_acumulados": ciclos_novos,
            "rul_percentual": max(0, 100 - (ciclos_novos // 50)),
            "status": "ATENÇÃO" if atraso > 200 else "NORMAL"
        })
    
    time.sleep(0.5)
    st.rerun()
