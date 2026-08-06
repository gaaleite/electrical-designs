import streamlit as st
import os
import matplotlib.pyplot as plt
import pandas as pd
import json
from google import genai
from google.genai import types

# 1. Configuração da Página Profissional
st.set_page_config(
    page_title="CAD/IA - Painéis Elétricos Industriais", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS para emular interface Dark de Softwares CAD
st.markdown("""
    <style>
    .cad-header { font-size: 26px; font-weight: bold; color: #00FFCC; border-bottom: 2px solid #00FFCC; margin-bottom: 20px; }
    .metric-box { background-color: #1E1E1E; border-left: 4px solid #00FFCC; padding: 10px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ CAD & Roteador Industrial Inteligente")

# --- BANCO DE DADOS DE MATERIAIS (Preços de referência) ---
TABELA_PRECOS = {
    "Disjuntor Motor": 180.00,
    "Disjuntor Trifásico": 120.00,
    "Contator de Potência": 145.00,
    "Relé Térmico": 95.00,
    "Barramento Cobre (Espinho)": 350.00,
    "Chave Seccionadora": 280.00,
    "Bloco DPS": 110.00,
    "Fonte Chaveada 24V": 215.00,
    "CLP Industrial": 1850.00
}

# --- INICIALIZAÇÃO DOS ESTADOS DA SESSÃO (PERSISTÊNCIA) ---
if "componentes" not in st.session_state:
    st.session_state["componentes"] = pd.DataFrame([
        {"id": 1, "Tag/Nome": "QG1 (Geral)", "Tipo": "Chave Seccionadora", "Qtd": 1},
        {"id": 2, "Tag/Nome": "K1", "Tipo": "Contator de Potência", "Qtd": 1},
        {"id": 3, "Tag/Nome": "F1", "Tipo": "Disjuntor Trifásico", "Qtd": 16},
        {"id": 4, "Tag/Nome": "DPS1", "Tipo": "Bloco DPS", "Qtd": 1}
    ])

if "conexoes" not in st.session_state:
    st.session_state["conexoes"] = pd.DataFrame([
        {"origem_id": 1, "destino_id": 2, "cor_fio": "Vermelho"},
        {"origem_id": 2, "destino_id": 3, "cor_fio": "Preto"}
    ])

# --- NAVEGAÇÃO ENTRE AS 3 ÁREAS DE ENGENHARIA ---
st.sidebar.header("🕹️ Centro de Operações")
ambiente = st.sidebar.radio(
    "Mudar ambiente de trabalho:",
    [
        "📊 1. Dimensionamento e Orçamento",
        "📐 2. Diagrama e Layout (Estilo AutoCAD)",
        "🤖 3. Assistente de IA Cooperativo (RAG/Upload)"
    ]
)

# MAPA DE CORES SEGURO PARA O MATPLOTLIB
mapeamento_cores = {
    "preto": "black", "azul": "blue", "vermelho": "red", 
    "verde": "green", "amarelo": "gold", "cinza": "gray"
}

# ==========================================
# AMBIENTE 1: DIMENSIONAMENTO E ORÇAMENTO
# ==========================================
if ambiente == "📊 1. Dimensionamento e Orçamento":
    st.markdown('<div class="cad-header">📊 Engenharia de Materiais & Custos</div>', unsafe_allow_html=True)
    st.markdown("Defina os componentes físicos do painel para gerar a estimativa de custos em tempo real.")

    # Edição dinâmica da tabela de componentes do painel
    st.subheader("Componentes do Quadro Elétrico")
    df_editado = st.data_editor(
        st.session_state["componentes"], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_componentes"
    )
    st.session_state["componentes"] = df_editado

    # Cálculo dinâmico do orçamento baseado nos preços homologados
    total_painel = 0.0
    itens_cotados = []
    
    for _, row in df_editado.iterrows():
        tipo = row.get("Tipo", "")
        qtd = pd.to_numeric(row.get("Qtd", 0), errors='coerce')
        if pd.isna(qtd): qtd = 0
            
        preco_unit = TABELA_PRECOS.get(tipo, 50.00) # R$50 padrão para itens genéricos
        subtotal = preco_unit * qtd
        total_painel += subtotal
        itens_cotados.append({
            "Componente": row.get("Tag/Nome", f"Comp_{row.get('id')}"),
            "Especificação": tipo,
            "Qtd": qtd,
            "Preço Unitário (R$)": f"R$ {preco_unit:,.2f}",
            "Subtotal (R$)": f"R$ {subtotal:,.2f}"
        })

    # Display de KPIs de Engenharia Financeira
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><h4>Custo Estimado do Painel</h4><h2>R$ {total_painel:,.2f}</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><h4>Total de Dispositivos Ativos</h4><h2>{int(df_editado["Qtd"].sum())} unidades</h2></div>', unsafe_allow_html=True)

    st.subheader("📋 Resumo Executivo para Compras")
    st.table(pd.DataFrame(itens_cotados))

# ==========================================
# AMBIENTE 2: DIAGRAMA E LAYOUT (AUTOCAD)
# ==========================================
elif ambiente == "📐 2. Diagrama e Layout (Estilo AutoCAD)":
    st.markdown('<div class="cad-header">📐 Canvas de Roteamento (Visualização CAD)</div>', unsafe_allow_html=True)
    
    col_config, col_canvas = st.columns()
    
    with col_config:
        st.subheader("Gerenciar Conexões")
        df_fios = st.data_editor(
            st.session_state["conexoes"],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_fios"
        )
        st.session_state["conexoes"] = df_fios
        
    with col_canvas:
        # Geração dinâmica de coordenadas geométricas baseadas no ID para simular o Grid
        comp_df = st.session_state["componentes"]
        posicoes = {}
        
        # Distribui componentes de forma horizontal uniforme no Grid do painel
        passo_x = 800 / (len(comp_df) if len(comp_df) > 0 else 1)
        for i, (_, row) in enumerate(comp_df.iterrows()):
            c_id = row.get("id")
            if pd.isna(c_id): continue
            posicoes[int(c_id)] = {
                "x": 100 + (i * passo_x * 0.8),
                "y": 250,
                "nome": str(row.get("Tag/Nome", f"ID {c_id}"))
            }

        # Inicialização do Canvas com Estilo Fundo Escuro do AutoCAD (Grid)
        fig, ax = plt.subplots(figsize=(11, 6), facecolor='#151515')
        ax.set_facecolor('#151515')
        
        largura_box, altura_box = 80, 110
        
        # Desenha os cubículos/componentes no padrão técnico
        for c_id, pos in posicoes.items():
            rect = plt.Rectangle(
                (pos["x"] - largura_box/2, pos["y"] - altura_box/2), 
                largura_box, altura_box, 
                facecolor='#2A2A2A', edgecolor='#00FFCC', linewidth=2
            )
            ax.add_patch(rect)
            ax.text(pos["x"], pos["y"], pos["nome"], ha='center', va='center', color='white', fontsize=10, fontweight='bold')
            
        # Processamento das linhas de fiação elétrica com desvios ortogonais
        for _, fio in df_fios.iterrows():
            try:
                origem = posicoes.get(int(fio["origem_id"]))
                destino = posicoes.get(int(fio["destino_id"]))
                if not origem or not destino: continue
                
                # Geometria Ortogonal (Linhas retas tipo CAD)
                meio_x = (origem["x"] + destino["x"]) / 2
                xs = [origem["x"], meio_x, meio_x, destino["x"]]
                ys = [origem["y"], origem["y"], destino["y"], destino["y"]]
                
                cor_crua = str(fio.get("cor_fio", "Azul")).strip().lower()
                cor_plot = mapeamento_cores.get(cor_crua, "cyan")
                
                ax.plot(xs, ys, color=cor_plot, linewidth=2, linestyle='-')
                # Desenha seta indicando direção da corrente
                ax.annotate('', xy=(destino["x"], destino["y"]), xytext=(meio_x, destino["y"]),
                            arrowprops=dict(arrowstyle="->", color=cor_plot, lw=1.5))
            except Exception:
                continue

        # Configurações do Grid Técnico CAD
        ax.set_xlim(0, 1000)
        ax.set_ylim(0, 500)
        ax.grid(True, color='#252525', linestyle='--', linewidth=0.5)
        ax.invert_yaxis()
        
        # Remove bordas padrão mantendo apenas o grid interno escuro
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.xaxis.set_tick_params(colors='#555555')
        ax.yaxis.set_tick_params(colors='#555555')
        
        st.pyplot(fig)


# ==========================================
# AMBIENTE 3: ASSISTENTE DE IA COOPERATIVO
# ==========================================
elif ambiente == "🤖 3. Assistente de IA Cooperativo (RAG/Upload)":
    st.markdown('<div class="cad-header">🤖 Engenharia Assistida por IA</div>', unsafe_allow_html=True)
    st.markdown("Suba arquivos de projetos anteriores (.json, .csv) e utilize a IA contextualizada para projetar novos diagramas.")

    # Área de Contextualização de Projetos Anteriores (Base de Conhecimento)
    projetos_referencia = st.file_uploader(
        "Upload de Projetos Base (Alimente a memória da IA):", 
        type=["json", "csv", "xlsx"], 
        accept_multiple_files=True
    )
    
    if projetos_referencia:
        st.info(f"📂 {len(projetos_referencia)} projeto(s) acoplado(s) à memória contextual do modelo.")

    prompt_ia = st.text_area(
        "Instruções do novo diagrama:",
        value="Gere uma malha contendo 1 CLP principal conectado a 3 contatores de motor e proteção por disjuntores industriais."
    )

    if st.button("Executar Engenharia Cognitiva"):
        api_key_local = st.secrets.get("GEMINI_API_KEY")
        if not api_key_local:
            st.error("❌ Erro: Chave 'GEMINI_API_KEY' ausente nos Secrets.")
        else:
            with st.spinner("Modelando arquitetura elétrica baseada nas referências..."):
                try:
                    client_local = genai.Client(api_key=api_key_local.strip())
                    
                    # Leitura dos arquivos upados para injetar no sistema de contexto
                    conteudo_referencia = ""
                    for p in projetos_referencia:
                        conteudo_referencia += f"\n[Arquivo de Referência: {p.name}]\n"
                        conteudo_referencia += p.read().decode("utf-8", errors="ignore")[:2000] # Evita estouro de tokens de arquivos massivos
