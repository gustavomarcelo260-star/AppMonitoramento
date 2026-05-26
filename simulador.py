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
    [data-testid="stAppViewContainer"] { background-color: #070B14; }
    .stButton > button { background: #2563EB !important; color: white !important; border: none !important; }
    .panel { background: #151E2E; padding: 20px; border-radius: 8px; border: 1px solid #1E293B; }
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
# LOGICA DE SIMULAÇÃO
# =========================================================
st.title("⚙️ Simulador de Planta Industrial")
st.markdown("Gerador de telemetria para validação do sistema supervisório.")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Configurações de Ativo")
    tag_clp = st.selectbox("Simular Tag CLP:", ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04", "SIM_CLP_05"])
    tag_vib = st.selectbox("Simular Sensor Vibração:", ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04", "SIM_VIB_05"])
    
    ciclos = st.number_input("Número de Ciclos a Gerar", min_value=1, max_value=100, value=10)
    delay_falha = st.slider("Atraso de Desgaste (ms)", 0, 500, 0)
    vib_anomalia = st.slider("Intensidade da Vibração (mm/s)", 1.0, 10.0, 2.0)

with col2:
    st.markdown("### Console de Execução")
    if st.button("Iniciar Geração de Dados", type="primary"):
        progresso = st.progress(0)
        status_text = st.empty()
        
        for i in range(ciclos):
            status_text.text(f"Gerando ciclo {i+1} de {ciclos} para {tag_clp}...")
            agora = datetime.now(timezone.utc).isoformat()
            
            # Payload CLP
            payload_clp = {
                "nome_identificacao": "Cilindro Simulado",
                "tag_clp_vinculada": tag_clp,
                "ciclos_acumulados": i + 1,
                "tempo_avanco_ms": round(1200 + delay_falha + random.uniform(-10, 10), 2),
                "tempo_retorno_ms": round(1100 + random.uniform(-10, 10), 2),
                "timestamp": agora,
                "status": "NORMAL" if delay_falha < 200 else "ATENÇÃO"
            }
            
            # Payload Vibração
            payload_vib = {
                "id_sensor_vinculado": tag_vib,
                "vibracao_rms": round(vib_anomalia + random.uniform(-0.5, 0.5), 2),
                "timestamp": agora
            }
            
            # Gravação no Firestore (Telemetria)
            db.collection('telemetria_clp').add(payload_clp)
            db.collection('telemetria_vib').add(payload_vib)
            
            # Atualização de status no cilindro pai para o Dashboard ler
            docs = db.collection('cilindros_ativos').where('tag_clp_vinculada', '==', tag_clp).stream()
            for doc in docs:
                db.collection('cilindros_ativos').document(doc.id).update({
                    "ciclos_acumulados": i + 1,
                    "status": "ATENÇÃO" if delay_falha > 200 else "NORMAL"
                })
            
            progresso.progress((i + 1) / ciclos)
            time.sleep(0.5)
            
        status_text.success("Lote de telemetria enviado com sucesso ao Firebase.")

st.markdown("---")
st.info("Nota: Este app não possui interface de visualização. Ele serve apenas como injetor de dados para que o 'Sistema Supervisório Central' os processe.")
