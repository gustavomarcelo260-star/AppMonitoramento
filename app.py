import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone
import time

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Kopempack Operations Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CSS GLOBAL - TESLA & LOVABLE DARK OPS STYLE
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #070B14 !important;
    color: #F1F5F9;
}

[data-testid="stAppViewContainer"] {
    background: #070B14;
}

[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
}

#MainMenu, footer {
    visibility: hidden;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #0B111C;
    border-right: 1px solid #182234;
}

.sidebar-logo {
    text-align: center;
    padding-top: 10px;
    padding-bottom: 20px;
    border-bottom: 1px solid #182234;
    margin-bottom: 20px;
}

.sidebar-title {
    color: white;
    font-size: 22px;
    font-weight: 700;
    margin-top: 15px;
    letter-spacing: 0.15em;
}

.sidebar-subtitle {
    color: #6E7C93;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* HEADER HERO */
.hero-container {
    background: linear-gradient(135deg,#111827,#0B1220);
    border: 1px solid #1B263B;
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 25px;
}

.hero-title {
    color: white;
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 6px;
}

.hero-subtitle {
    color: #8CA0B8;
    font-size: 14px;
}

.hero-status {
    background: #0F1728;
    border: 1px solid #1E2B45;
    padding: 8px 14px;
    border-radius: 9999px;
    display: inline-block;
    margin-top: 14px;
    color: #10B981;
    font-size: 12px;
    font-weight: 600;
}

/* KPI CARDS */
.kpi-card {
    background: linear-gradient(180deg,#121A2B,#0D1422);
    border: 1px solid #1E2B45;
    border-radius: 12px;
    padding: 20px;
    height: 130px;
}

.kpi-title {
    color: #7F93AD;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.kpi-value {
    color: white;
    font-size: 36px;
    font-weight: 700;
    margin-top: 12px;
    line-height: 1;
}

.kpi-blue { border-left: 4px solid #3B82F6; }
.kpi-green { border-left: 4px solid #10B981; }
.kpi-red { border-left: 4px solid #EF4444; }
.kpi-yellow { border-left: 4px solid #F59E0B; }

/* REQUISITOS DE CONTAINER SEM QUEBRA */
div[data-key="painel_status"], 
div[data-key="painel_saude"], 
div[data-key="painel_frota"], 
div[data-key="painel_historico"] {
    background: #0E1625 !important;
    border: 1px solid #1D2940 !important;
    border-radius: 12px !important;
    padding: 20px !important;
    margin-top: 15px !important;
}

.panel-title {
    color: white;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 15px;
}

/* INPUTS E BOTÕES */
.stButton > button {
    width: 100%;
    border-radius: 8px !important;
    border: none !important;
    background: #2563EB !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 10px !important;
}

.stButton > button:hover { background: #1D4ED8 !important; }

.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background: #111827 !important;
    border: 1px solid #1E293B !important;
    color: white !important;
    border-radius: 8px !important;
}

.alert-box {
    background: #101826;
    border: 1px solid #1F2A40;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 10px;
}

.alert-title { color: white; font-weight: 600; font-size: 13px; }
.alert-sub { color: #8CA0B8; font-size: 12px; margin-top: 2px; }

.custom-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
.custom-table th { padding: 12px; color: #7F93AD; text-transform: uppercase; font-size: 11px; border-bottom: 1px solid #1D2940; }
.custom-table td { padding: 12px; border-bottom: 1px solid rgba(29, 41, 64, 0.5); color: #F1F5F9; }
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
# PIPELINE DE CONSOLIDACAO DE TELEMETRIA
# =========================================================
def obter_ativos_consolidados():
    ativos = buscar_cilindros()
    if not ativos:
        return []
    
    clp_stream = db.collection('estado_atual_clp').stream()
    clp_docs = [d.to_dict() for d in clp_stream]
    df_clp = pd.DataFrame(clp_docs) if clp_docs else pd.DataFrame()
    
    vib_stream = db.collection('estado_atual_vib').stream()
    vib_docs = [d.to_dict() for d in vib_stream]
    df_vib = pd.DataFrame(vib_docs) if vib_docs else pd.DataFrame()
    
    lista_consolidada = []
    
    for ativo in ativos:
        tag = ativo['tag_clp_vinculada']
        sensor = ativo['id_sensor_vinculado']
        
        t_avanco = 0.0
        t_retorno = 0.0
        ciclos = 0
        vibracao = 0.0
        
        if not df_clp.empty and 'tag_clp' in df_clp.columns:
            sub_clp = df_clp[df_clp['tag_clp'] == tag]
            if not sub_clp.empty:
                latest_clp = sub_clp.iloc[0]
                t_avanco = latest_clp.get('tempo_avanco_ms', 0.0)
                t_retorno = latest_clp.get('tempo_retorno_ms', 0.0)
                ciclos = latest_clp.get('total_cycles', 0)
                
        if not df_vib.empty and 'id_sensor' in df_vib.columns:
            sub_vib = df_vib[df_vib['id_sensor'] == sensor]
            if not sub_vib.empty:
                latest_vib = sub_vib.iloc[0]
                vibracao = latest_vib.get('vibracao_rms', 0.0)
                
        b_avanco = ativo.get('baseline_avanco_ms', 0.0)
        b_retorno = ativo.get('baseline_retorno_ms', 0.0)
        aprendizado_concluido = ativo.get('modo_aprendizado_concluido', False)
        
        # SOLUÇÃO BYPASS ÍNDICE COMPOSTO: Filtra na memória via Pandas
        if ciclos >= 100 and not aprendizado_concluido:
            historico_stream = db.collection('telemetria_clp')\
                                 .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                                 .limit(200)\
                                 .stream()
            all_pontos = [d.to_dict() for d in historico_stream]
            
            if all_pontos:
                df_all_p = pd.DataFrame(all_pontos)
                df_filtrado = df_all_p[df_all_p['tag_clp'] == tag].head(10)
                
                if not df_filtrado.empty:
                    b_avanco = round(df_filtrado['tempo_avanco_ms'].mean(), 1)
                    b_retorno = round(df_filtrado['tempo_retorno_ms'].mean(), 1)
                else:
                    b_avanco, b_retorno = t_avanco, t_retorno
            else:
                b_avanco, b_retorno = t_avanco, t_retorno
                
            aprendizado_concluido = True
            atualizar_status_cilindro(ativo['id_documento'], {
                "baseline_avanco_ms": b_avanco,
                "baseline_retorno_ms": b_retorno,
                "modo_aprendizado_concluido": True
            })
            
        if ciclos < 100:
            status = "APRENDIZADO"
            health = 100
        else:
            desvio_ava = (t_avanco - b_avanco) / b_avanco if b_avanco > 0 else 0
            desvio_ret = (t_retorno - b_retorno) / b_retorno if b_retorno > 0 else 0
            
            pior_desvio_pos = max(0, desvio_ava, desvio_ret)
            pior_desvio_neg = min(0, desvio_ava, desvio_ret)
            
            if abs(pior_desvio_neg) > pior_desvio_pos:
                health = max(0, 100 - int(abs(pior_desvio_neg) * 300))
            else:
                health = max(0, 100 - int(pior_desvio_pos * 200))
            
            if desvio_ava > 0.30 or desvio_ret > 0.30 or desvio_ava < -0.20 or desvio_ret < -0.20 or vibracao > 8.0 or ativo.get('falha_manual', False):
                status = "FALHA IMINENTE"
            elif desvio_ava > 0.15 or desvio_ret > 0.15 or vibracao > 4.0:
                status = "ATENÇÃO"
            else:
                status = "NORMAL"
                
        lista_consolidada.append({
            **ativo,
            "tempo_avanco_ms": t_avanco,
            "tempo_retorno_ms": t_retorno,
            "ciclos_acumulados": ciclos,
            "vibracao_rms": vibracao,
            "baseline_avanco_ms": b_avanco,
            "baseline_retorno_ms": b_retorno,
            "status": status,
            "health_score": health
        })
        
    return lista_consolidada

def hero_header():
    horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Kopempack Operations Center</div>
        <div class="hero-subtitle">Monitoramento Industrial • Telemetria Sensor-Sensor • Análise Preditiva Edge</div>
        <div class="hero-status">🟢 REDE ONLINE • AUTO-REFRESH ATIVO: {horario}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# TELA: DASHBOARD
# =========================================================
def tela_dashboard():
    hero_header()
    dados = obter_ativos_consolidados()
    
    if not dados:
        st.warning("Nenhum ativo comissionado na planta virtual.")
        return
        
    df = pd.DataFrame(dados)
    total = len(df)
    alertas = len(df[df['status'] == 'ATENÇÃO'])
    falhas = len(df[df['status'] == 'FALHA IMINENTE'])
    media_health = round(df['health_score'].mean(), 1)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi("Ativos Monitorados", total, "kpi-blue")
    with c2: render_kpi("Alertas de Sistema", alertas, "kpi-yellow")
    with c3: render_kpi("Falhas Críticas", falhas, "kpi-red")
    with c4: render_kpi("Health Score Médio", f"{media_health}%", "kpi-green")
    
    g1, g2 = st.columns(2)
    with g1:
        with st.container(key="painel_status"):
            st.markdown('<div class="panel-title">Status de Operação Global</div>', unsafe_allow_html=True)
            fig = px.pie(
                df, names='status', hole=0.70, color='status',
                color_discrete_map={'NORMAL': '#10B981', 'ATENÇÃO': '#F59E0B', 'FALHA IMINENTE': '#EF4444', 'APRENDIZADO': '#3B82F6'}
            )
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=320, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
    with g2:
        with st.container(key="painel_saude"):
            st.markdown('<div class="panel-title">Índice de Saúde por Ativo</div>', unsafe_allow_html=True)
            df_sorted = df.sort_values(by='health_score', ascending=True)
            fig2 = px.bar(
                df_sorted, x='health_score', y='nome_identificacao', orientation='h', color='health_score',
                color_continuous_scale=['#EF4444', '#F59E0B', '#10B981'], range_color=[0, 100]
            )
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=320, xaxis_title="Health Score %", yaxis_title="", coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)
        
    t1, t2 = st.columns([7, 3])
    with t1:
        with st.container(key="painel_frota"):
            st.markdown('<div class="panel-title">Frota de Cilindros Ativos</div>', unsafe_allow_html=True)
            html_table = """<table class="custom-table"><thead><tr>
                <th>Identificação</th><th>Tag CLP</th><th>ID Sensor</th><th>Avanço</th><th>Retorno</th><th>Vibração</th><th>Saúde</th><th>Status</th>
            </tr></thead><tbody>"""
            for _, r in df.iterrows():
                badge_color = "#10B981" if r['status']=='NORMAL' else ("#F59E0B" if r['status']=='ATENÇÃO' else ("#EF4444" if r['status']=='FALHA IMINENTE' else "#3B82F6"))
                html_table += f"""<tr>
                    <td><b>{r['nome_identificacao']}</b></td>
                    <td><span style="font-family:monospace; color:#8CA0B8;">{r['tag_clp_vinculada']}</span></td>
                    <td><span style="font-family:monospace; color:#8CA0B8;">{r['id_sensor_vinculado']}</span></td>
                    <td>{r['tempo_avanco_ms']} ms</td>
                    <td>{r['tempo_retorno_ms']} ms</td>
                    <td>{r['vibracao_rms']} mm/s</td>
                    <td><b>{r['health_score']}%</b></td>
                    <td><span style="color:{badge_color}; font-weight:600;">{r['status']}</span></td>
                </tr>"""
            html_table += "</tbody></table>"
            st.markdown(html_table, unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="panel"><div class="panel-title">Eventos de Borda IIoT</div>', unsafe_allow_html=True)
        for _, r in df.iterrows():
            if r['status'] == "FALHA IMINENTE":
                st.markdown(f'<div class="alert-box"><div class="alert-title">🚨 Crítico: {r["nome_identificacao"]}</div><div class="alert-sub">Anomalia severa detetada fora das tolerâncias.</div></div>', unsafe_allow_html=True)
            elif r['status'] == "ATENÇÃO":
                st.markdown(f'<div class="alert-box"><div class="alert-title">⚠️ Alerta: {r["nome_identificacao"]}</div><div class="alert-sub">Desvio de ciclo em relação à baseline estável.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="alert-box"><div class="alert-title">🟢 Gateway Sincronizado</div><div class="alert-sub">Transmissão ativa via MQTT.</div></div>', unsafe_allow_html=True)

# =========================================================
# TELA: COMISSIONAMENTO
# =========================================================
def tela_comissionamento():
    hero_header()
    st.markdown("### Módulo de Comissionamento Industrial")
    st.markdown("Vínculo lógico entre variáveis de hardware geradas no campo e ativos físicos.")
    
    col1, col2 = st.columns(2)
    tags_clp_disponiveis = ["SIM_CLP_01", "SIM_CLP_02", "SIM_CLP_03", "SIM_CLP_04", "SIM_CLP_05"]
    tags_vib_disponiveis = ["SIM_VIB_01", "SIM_VIB_02", "SIM_VIB_03", "SIM_VIB_04", "SIM_VIB_05"]
    
    with col1:
        st.markdown("#### Endereçamento de Tags")
        tag_clp = st.selectbox("Vincular Registrador CLP (Tempo)", tags_clp_disponiveis)
        tag_vib = st.selectbox("Vincular Endereço Sensor (Vibração)", tags_vib_disponiveis)
        
    with col2:
        st.markdown("#### Propriedades do Ativo")
        nome = st.text_input("Nomenclatura Funcional (Ex: Cilindro Prensa Estação 3)")
        modelo = st.selectbox("Modelo Pneumático", ["ISO 15552 - 32mm", "ISO 15552 - 50mm", "Compacto ADN"])
        
    if st.button("Gravar Vínculo no Sistema"):
        if not nome:
            st.error("Campo de nomenclatura funcional é obrigatório.")
            return
        payload = {
            "nome_identificacao": nome, "modelo": modelo, "tag_clp_vinculada": tag_clp,
            "id_sensor_vinculado": tag_vib, "estado_integridade": "ORIGINAL", "modo_aprendizado_concluido": False,
            "baseline_avanco_ms": 0.0, "baseline_retorno_ms": 0.0, "falha_manual": False
        }
        registrar_cilindro(payload)
        st.success(f"Ativo '{nome}' comissionado com sucesso.")

# =========================================================
# TELA: DIAGNÓSTICO
# =========================================================
def tela_diagnostico():
    hero_header()
    dados = obter_ativos_consolidados()
    
    if not dados:
        st.warning("Nenhum ativo localizado para inspeção técnica.")
        return
        
    mapa = {c['nome_identificacao']: c for c in dados}
    selecao = st.selectbox("Selecione o Ativo para Diagnóstico Avançado:", list(mapa.keys()))
    ativo = mapa[selecao]
    id_doc = ativo['id_documento']
    health = ativo['health_score']
    tag = ativo['tag_clp_vinculada']
    sensor = ativo['id_sensor_vinculado']
    
    col_g, col_m = st.columns([1, 2])
    with col_g:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=health,
            number={'suffix': '%', 'font': {'size': 38, 'color': 'white'}},
            gauge={
                'axis': {'range': [0, 100], 'visible': False}, 'bar': {'color': '#2563EB'}, 'bgcolor': '#111827',
                'steps': [{'range': [0, 40], 'color': 'rgba(239, 68, 68, 0.2)'}, {'range': [40, 75], 'color': 'rgba(245, 158, 11, 0.2)'}, {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.1)'}]
            }
        ))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        
    with col_m:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Tempo Avanço (Último)", f"{ativo['tempo_avanco_ms']} ms", f"Base: {ativo['baseline_avanco_ms']} ms", delta_color="inverse")
        c2.metric("Tempo Retorno (Último)", f"{ativo['tempo_retorno_ms']} ms", f"Base: {ativo['baseline_retorno_ms']} ms", delta_color="inverse")
        c3.metric("Vibração de Campo", f"{ativo['vibracao_rms']} mm/s")
        
        c1.metric("Ciclos Totais (CLP)", f"{ativo['ciclos_acumulados']:,}".replace(",", "."))
        c2.metric("Condição Logística", ativo['estado_integridade'])
        c3.metric("Status Operacional", ativo['status'])

    with st.container(key="painel_historico"):
        st.markdown('<div class="panel-title">Histórico de Séries Temporais Ciclo a Ciclo</div>', unsafe_allow_html=True)
        
        clp_stream = db.collection('telemetria_clp').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(150).stream()
        df_clp_h = pd.DataFrame([d.to_dict() for d in clp_stream])
        
        vib_stream = db.collection('telemetria_vib').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(150).stream()
        df_vib_h = pd.DataFrame([d.to_dict() for d in vib_stream])
        
        if not df_clp_h.empty and 'tag_clp' in df_clp_h.columns:
            df_clp_h = df_clp_h[df_clp_h['tag_clp'] == tag].head(30).reset_index(drop=True)
            
        if not df_vib_h.empty and 'id_sensor' in df_vib_h.columns:
            df_vib_h = df_vib_h[df_vib_h['id_sensor'] == sensor].head(30).reset_index(drop=True)
            
        if not df_clp_h.empty and not df_vib_h.empty and 'total_cycles' in df_clp_h.columns:
            min_len = min(len(df_clp_h), len(df_vib_h))
            df_hist = pd.concat([df_clp_h.iloc[:min_len], df_vib_h.get(['vibracao_rms']).iloc[:min_len]], axis=1)
            df_hist = df_hist.iloc[::-1].reset_index(drop=True)
            
            fig_line = make_subplots(secondary_y=True)
            fig_line.add_trace(go.Scatter(x=df_hist['total_cycles'], y=df_hist['tempo_avanco_ms'], name="Tempo Avanço (ms)", line=dict(color='#3B82F6', width=2)), secondary_y=False)
            fig_line.add_trace(go.Scatter(x=df_hist['total_cycles'], y=df_hist['tempo_retorno_ms'], name="Tempo Retorno (ms)", line=dict(color='#F59E0B', width=2)), secondary_y=False)
            fig_line.add_trace(go.Scatter(x=df_hist['total_cycles'], y=df_hist['vibracao_rms'], name="Vibração (mm/s)", line=dict(color='#10B981', width=1.5, dash='dot')), secondary_y=True)
            
            b_av = ativo['baseline_avanco_ms']
            b_ret = ativo['baseline_retorno_ms']
            if b_av > 0:
                fig_line.add_hline(y=b_av, line_dash="dash", line_color="rgba(59, 130, 246, 0.4)", annotation_text="Base Av.")
                fig_line.add_hline(y=b_av * 1.30, line_dash="solid", line_color="rgba(239, 68, 68, 0.4)", annotation_text="+30%")
                fig_line.add_hline(y=b_av * 0.80, line_dash="solid", line_color="rgba(239, 68, 68, 0.4)", annotation_text="-20%")
            if b_ret > 0:
                fig_line.add_hline(y=b_ret, line_dash="dash", line_color="rgba(245, 158, 11, 0.4)", annotation_text="Base Ret.")

            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), height=350,
                xaxis_title="Sequência de Ciclos (Contador CLP)", yaxis_title="Tempo (ms)", yaxis2_title="Vibração (mm/s)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Aguardando sincronização de buffers de histórico...")
        
    st.markdown("### Painel de Intervenção e Comandos Remotos")
    
    with st.container():
        a1, a2, a3 = st.columns(3)
        
        with a1:
            st.markdown("#### Recalibração Temporal")
            st.caption("Invalida o aprendizado anterior e força a captura de novas baselines.")
            if st.button("Forçar Nova Baseline"):
                atualizar_status_cilindro(id_doc, {"modo_aprendizado_concluido": False, "baseline_avanco_ms": 0.0, "baseline_retorno_ms": 0.0})
                st.success("Comando enviado. Iniciando ciclo de aprendizado.")
            
        with a2:
            st.markdown("#### Ordem de Manutenção")
            st.caption("Atualiza as tags patrimoniais após intervenção física de campo.")
            op = st.selectbox("Tipo de Intervenção", ["Ajuste/Reparo de Vedação", "Substituição Integral do Componente"])
            if st.button("Registrar Intervenção"):
                if "Substituição" in op:
                    atualizar_status_cilindro(id_doc, {"estado_integridade": "ORIGINAL", "modo_aprendizado_concluido": False, "baseline_avanco_ms": 0.0, "baseline_retorno_ms": 0.0, "falha_manual": False})
                    st.success("Componente resetado no log logístico.")
                else:
                    atualizar_status_cilindro(id_doc, {"estado_integridade": "REPARADO"})
                    st.warning("Status modificado para REPARADO.")
            
        with a3:
            st.markdown("#### Comando de Emergência")
            st.caption("Injeta uma flag de interrupção forçada para validação de alarmes.")
            if st.button("Forçar Sinalização de Quebra"):
                atualizar_status_cilindro(id_doc, {"falha_manual": True})
                st.error("Alerta de quebra propagado para a planta.")

# =========================================================
# HELPER COMPONENTS
# =========================================================
def render_kpi(titulo, valor, classe):
    st.markdown(f"""
    <div class="kpi-card {classe}">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{valor}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# MENUS & NAVEGAÇÃO
# =========================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-title">KOPEMPACK</div>
        <div class="sidebar-subtitle">Operations Center</div>
    </div>
    """, unsafe_allow_html=True)
    
    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Comissionamento", "Diagnóstico"],
        icons=["speedometer2", "cpu", "activity"],
        default_index=0,
        styles={
            "container": {"background-color": "#0B111C", "padding": "0!important"},
            "icon": {"color": "#3B82F6", "font-size": "18px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "6px", "border-radius": "8px", "--hover-color": "#111827", "color": "white"},
            "nav-link-selected": {"background-color": "#2563EB"}
        }
    )

if menu == "Dashboard":
    tela_dashboard()
    time.sleep(4.0)
    st.rerun()
elif menu == "Comissionamento":
    tela_comissionamento()
elif menu == "Diagnóstico":
    tela_diagnostico()
    time.sleep(4.0)
    st.rerun()
