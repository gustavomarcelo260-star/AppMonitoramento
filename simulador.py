import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import time
from datetime import datetime, timezone

# =========================================================
# CONFIGURAÇÃO DA INTERFACE
# =========================================================
st.set_page_config(page_title="Kopempack - Injetor de Telemetria IIoT", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0B101B !important; color: #F1F5F9; }
    [data-testid="stAppViewContainer"] { background-color: #0B101B; }
    [data-testid="stHeader"] { background: transparent !important; }
    .station-card { background-color: #151E2E; border: 1px solid #1E293B; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }
    .station-header { font-size: 1rem; font-weight: 600; color: #3B82F6; margin-bottom: 1rem; border-bottom: 1px solid #1E293B; padding-bottom: 0.5rem; }
    .stButton > button { width: 100%; font-weight: 600 !important; border-radius: 0.375rem !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONEXÃO FIREBASE
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
# INICIALIZAÇÃO DE ESTADO LOCAL (5 CILINDROS)
# =========================================================
ESTACOES_HARDWARE = [
    {"clp": "SIM_CLP_01", "vib": "SIM_VIB_01"},
    {"clp": "SIM_CLP_02", "vib": "SIM_VIB_02"},
    {"clp": "SIM_CLP_03", "vib": "SIM_VIB_03"},
    {"clp": "SIM_CLP_04", "vib": "SIM_VIB_04"},
    {"clp": "SIM_CLP_05", "vib": "SIM_VIB_05"}
]

if 'running' not in st.session_state:
    st.session_state.running = False

for est in ESTACOES_HARDWARE:
    if f"ciclos_{est['clp']}" not in st.session_state:
        st.session_state[f"ciclos_{est['clp']}"] = 0

# =========================================================
# INTERFACE DE CONTROLE
# =========================================================
st.title("⚙️ Injetor de Telemetria de Campo (Gateway IIoT)")
st.markdown("Emulação física de sinais elétricos de sensores magnéticos (Sensor-Sensor) e analíticos de vibração.")

c1, c2, c3 = st.columns([1, 1, 8])
with c1:
    if st.button("▶️ INICIAR REDE", type="primary", use_container_width=True):
        st.session_state.running = True
with c2:
    if st.button("⏹️ PARAR REDE", use_container_width=True):
        st.session_state.running = False

st.markdown("---")

for est in ESTACOES_HARDWARE:
    clp_id = est['clp']
    vib_id = est['vib']
    
    st.markdown(f'<div class="station-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="station-header">Ponto de Medição: {clp_id} / {vib_id}</div>', unsafe_allow_html=True)
    
    col_info, col_sl1, col_sl2, col_sl3 = st.columns([2, 3, 3, 3])
    
    with col_info:
        st.metric("Ciclos Processados no CLP", f"{st.session_state[f'ciclos_{clp_id}']:,}".replace(",", "."))
        
    with col_sl1:
        st.slider("Tempo de Avanço (ms)", min_value=100.0, max_value=2000.0, value=400.0, step=10.0, key=f"val_avanco_{clp_id}")
        
    with col_sl2:
        st.slider("Tempo de Retorno (ms)", min_value=100.0, max_value=2000.0, value=380.0, step=10.0, key=f"val_retorno_{clp_id}")
        
    with col_sl3:
        st.slider("Vibração RMS (mm/s)", min_value=0.5, max_value=12.0, value=1.8, step=0.1, key=f"val_vib_{vib_id}")
        
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# LOOP DE EXECUÇÃO DA TRANSMISSÃO (OTIMIZADO)
# =========================================================
if st.session_state.running:
    agora = datetime.now(timezone.utc).isoformat()
    
    for est in ESTACOES_HARDWARE:
        clp_id = est['clp']
        vib_id = est['vib']
        
        st.session_state[f"ciclos_{clp_id}"] += 1
        
        val_avanco = round(st.session_state[f"val_avanco_{clp_id}"] + random.uniform(-5.0, 5.0), 1)
        val_retorno = round(st.session_state[f"val_retorno_{clp_id}"] + random.uniform(-5.0, 5.0), 1)
        val_vib = round(st.session_state[f"val_vib_{vib_id}"] + random.uniform(-0.1, 0.1), 2)
        
        payload_clp = {
            "tag_clp": clp_id,
            "tempo_avanco_ms": val_avanco,
            "tempo_retorno_ms": val_retorno,
            "total_cycles": st.session_state[f"ciclos_{clp_id}"],
            "timestamp": agora
        }
        
        payload_vib = {
            "id_sensor": vib_id,
            "vibracao_rms": val_vib,
            "timestamp": agora
        }
        
        # Escrita em documentos fixos de estado atual (Sobreescreve para poupar cotas)
        db.collection('estado_atual_clp').document(clp_id).set(payload_clp)
        db.collection('estado_atual_vib').document(vib_id).set(payload_vib)
        
        # Gravação de histórico reduzida (Apenas 1 ponto a cada 10 ciclos)
        if st.session_state[f"ciclos_{clp_id}"] % 10 == 0:
            db.collection('telemetria_clp').add(payload_clp)
            db.collection('telemetria_vib').add(payload_vib)
        
    time.sleep(1.0)
    st.rerun()
