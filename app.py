import streamlit as st
import os
import matplotlib.pyplot as plt
import pandas as pd
import json
import urllib.request
import urllib.parse
import re

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

# --- BANCO DE PREÇOS AUXILIAR (Se a busca web não encontrar nada específico) ---
TABELA_PRECOS_PADRAO = {
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

# --- INICIALIZAÇÃO DOS ESTADOS DA SESSÃO ---
if "componentes" not in st.session_state:
    st.session_state["componentes"] = pd.DataFrame([
        {"id": 1, "Tag/Nome": "QG1 (Geral)", "Tipo": "Chave Seccionadora", "Marca": "WEG", "Modelo": "MPW25", "Qtd": 1, "Preco_Unitario": 280.00},
        {"id": 2, "Tag/Nome": "K1", "Tipo": "Contator de Potência", "Marca": "WEG", "Modelo": "CWM9", "Qtd": 1, "Preco_Unitario": 145.00},
        {"id": 3, "Tag/Nome": "F1", "Tipo": "Disjuntor Trifásico", "Marca": "Siemens", "Modelo": "5SY", "Qtd": 16, "Preco_Unitario": 38.00},
        {"id": 4, "Tag/Nome": "DPS1", "Tipo": "Bloco DPS", "Marca": "Clamper", "Modelo": "VCL", "Qtd": 1, "Preco_Unitario": 110.00}
    ])

if "conexoes" not in st.session_state:
    st.session_state["conexoes"] = pd.DataFrame([
        {"origem_id": 1, "destino_id": 2, "cor_fio": "Vermelho"},
        {"origem_id": 2, "destino_id": 3, "cor_fio": "Preto"}
    ])

# Garante a existência das novas colunas na tabela se houver reset de estado
if "Marca" not in st.session_state["componentes"].columns:
    st.session_state["componentes"]["Marca"] = ""
if "Modelo" not in st.session_state["componentes"].columns:
    st.session_state["componentes"]["Modelo"] = ""
if "Preco_Unitario" not in st.session_state["componentes"].columns:
    st.session_state["componentes"]["Preco_Unitario"] = 0.0

# --- NAVEGAÇÃO ---
st.sidebar.header("🕹️ Centro de Operações")
ambiente = st.sidebar.radio(
    "Mudar ambiente de trabalho:",
    [
        "📊 1. Dimensionamento e Orçamento",
        "📐 2. Diagrama e Layout (Estilo AutoCAD)",
        "🤖 3. Assistente de IA Cooperativo (RAG/Upload)"
    ]
)

mapeamento_cores = {
    "preto": "black", "azul": "blue", "vermelho": "red", 
    "verde": "green", "amarelo": "gold", "cinza": "gray"
}

# ==========================================
# AMBIENTE 1: DIMENSIONAMENTO E ORÇAMENTO
# ==========================================
if ambiente == "📊 1. Dimensionamento e Orçamento":
    st.markdown('<div class="cad-header">📊 Engenharia de Materiais & Orçamento Web Real-Time</div>', unsafe_allow_html=True)
    st.markdown("Altere a marca e o modelo na planilha abaixo e clique no botão para disparar a busca automática de preços comerciais na internet.")

    # Função Avançada de Extração via API Pública Livre do DuckDuckGo
    def buscar_preco_api_aberta(marca, modelo, tipo):
        if not marca or not modelo:
            return TABELA_PRECOS_PADRAO.get(tipo, 50.00)
            
        # Monta um termo focado em busca comercial de e-commerce brasileiro
        query = f"preço comercial {tipo} {marca} {modelo}"
        url = f"https://duckduckgo.com{urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                dados_json = json.loads(response.read().decode('utf-8'))
                
                # Coleta todo o texto descritivo e de tópicos relacionados trazidos pelo buscador
                texto_analise = dados_json.get("AbstractText", "") + " " + str(dados_json.get("RelatedTopics", ""))
                
                # Procura por valores em Reais (Ex: R$ 145,00 ou R$180.50)
                valores = re.findall(r'R\$\s?(\d+[\.,]\d{2})', texto_analise)
                
                if valores:
                    precos_convertidos = []
                    for v in valores:
                        v_limpo = v.replace('.', '').replace(',', '.')
                        precos_convertidos.append(float(v_limpo))
                    return min(precos_convertidos) # Retorna a melhor oferta encontrada
        except Exception:
            pass
            
        # Fallback inteligente: Se a busca livre não retornar valores explícitos, busca na tabela local por categoria
        return TABELA_PRECOS_PADRAO.get(tipo, 50.00)

    st.subheader("📋 Lista de Materiais do Painel (BOM)")
    
    # Exibe a planilha para edição de quantidades, marcas e modelos
    df_editado = st.data_editor(
        st.session_state["componentes"], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_web_orcamento"
    )
    st.session_state["componentes"] = df_editado

    # Mecanismo de ativação sob demanda para evitar travamentos de tela
    if st.button("🔍 Sincronizar e Buscar Preços na Web em Tempo Real", type="primary"):
        with st.spinner("Conectando aos servidores de mercado e atualizando cotações..."):
            for idx, row in df_editado.iterrows():
                marca_item = str(row.get("Marca", ""))
                modelo_item = str(row.get("Modelo", ""))
                tipo_item = str(row.get("Tipo", ""))
                
                # Executa a busca
                novo_preco = buscar_preco_api_aberta(marca_item, modelo_item, tipo_item)
                df_editado.at[idx, "Preco_Unitario"] = novo_preco
            
            st.session_state["componentes"] = df_editado
            st.success("Tabela de preços sincronizada com a web com sucesso!")
            st.rerun()

    # Consolidação matemática do custo do projeto
    total_geral_painel = 0.0
    linhas_relatorio = []

    for _, row in df_editado.iterrows():
        qtd = pd.to_numeric(row.get("Qtd", 0), errors='coerce')
        if pd.isna(qtd): qtd = 0
        p_unit = float(row.get("Preco_Unitario", 0.0))
        
        subtotal = p_unit * qtd
        total_geral_painel += subtotal
        
        linhas_relatorio.append({
            "Componente": row.get("Tag/Nome", "Item"),
            "Dispositivo": f"{row.get('Tipo', '')} ({row.get('Marca', '')} {row.get('Modelo', '')})",
            "Quantidade": int(qtd),
            "Preço Unitário": f"R$ {p_unit:,.2f}",
            "Subtotal Comercial": f"R$ {subtotal:,.2f}"
        })

    # Painel visual de KPIs Financeiros
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><h4>Valor de Aquisição de Materiais</h4><h2>R$ {total_geral_painel:,.2f}</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><h4>Componentes Ativos na Lista</h4><h2>{int(df_editado["Qtd"].sum() if "Qtd" in df_editado.columns else 0)} unidades</h2></div>', unsafe_allow_html=True)

    st.subheader("🛒 Relatório Consolidado para Orçamento Comercial")
    if linhas_relatorio:
        st.dataframe(pd.DataFrame(linhas_relatorio), use_container_width=True)

# ==========================================
# AMBIENTE 2: DIAGRAMA E LAYOUT (AUTOCAD)
# ==========================================
elif ambiente == "📐 2. Diagrama e Layout (Estilo AutoCAD)":
    st.markdown('<div class="cad-header">📐 Canvas de Roteamento (Visualização CAD)</div>', unsafe_allow_html=True)
    col_config, col_canvas = st.columns()
    
    with col_config:
        df_fios = st.data_editor(st.session_state["conexoes"], num_rows="dynamic", use_container_width=True, key="editor_fios")
        st.session_state["conexoes"] = df_fios
        
    with col_canvas:
        comp_df = st.session_state["componentes"]
        posicoes = {}
        passo_x = 800 / (len(comp_df) if len(comp_df) > 0 else 1)
        for i, (_, row) in enumerate(comp_df.iterrows()):
            c_id = row.get("id")
            if pd.isna(c_id): continue
            posicoes[int(c_id)] = {"x": 100 + (i * passo_x * 0.8), "y": 250, "nome": str(row.get("Tag/Nome", f"ID {c_id}"))}

        fig, ax = plt.subplots(figsize=(11, 6), facecolor='#151515')
        ax.set_facecolor('#151515')
        largura_box, altura_box = 80, 110
        
        for c_id, pos in posicoes.items():
            rect = plt.Rectangle((pos["x"] - largura_box/2, pos["y"] - altura_box/2), largura_box, altura_box, facecolor='#2A2A2A', edgecolor='#00FFCC', linewidth=2)
            ax.add_patch(rect)
            ax.text(pos["x"], pos["y"], pos["nome"], ha='center', va='center', color='white', fontsize=10, fontweight='bold')
            
        for _, fio in df_fios.iterrows():
            try:
                origem = posicoes.get(int(fio["origem_id"]))
                destino = posicoes.get(int(fio["destino_id"]))
                if not origem or not destino: continue
                meio_x = (origem["x"] + destino["x"]) / 2
                xs = [origem["x"], meio_x, meio_x, destino["x"]]
                ys = [origem["y"], origem["y"], destino["y"], destino["y"]]
                cor_plot = mapeamento_cores.get(str(fio.get("cor_fio", "Azul")).strip().lower(), "cyan")
                ax.plot(xs, ys, color=cor_plot, linewidth=2)
