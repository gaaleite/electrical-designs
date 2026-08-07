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

# --- BANCO DE PREÇOS AUXILIAR ---
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
        {
            "id": 1, 
            "Nome": "", 
            "Marca": "", 
            "Ampere": "", 
            "Qtd": 1, 
            "Preco_Unitario": 0.0
        }
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
if "1." in ambiente:
    st.markdown('<div class="cad-header">📊 Engenharia de Materiais & Orçamento Web Real-Time</div>', unsafe_allow_html=True)
    st.markdown("Altere o Ampere na planilha abaixo e clique no botão para disparar a busca automática de preços comerciais na internet.")

    def buscar_preco_api_aberta(ampere, nome_item):
        # Se o usuário não digitou o nome do componente, usa o fallback padrão
        if not nome_item or str(nome_item).strip() == "":
            return TABELA_PRECOS_PADRAO.get(nome_item, 50.00)
            
        # Monta a query focada em trazer resultados comerciais de lojas
        query = f"preço comercial {nome_item} {ampere}".strip()
        url = f"https://duckduckgo.com{urllib.parse.quote(query)}"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
                # Captura padrões comuns de preços em páginas web (ex: R$ 150,00 ou R$150.00)
                valores_encontrados = re.findall(r'R\$\s?(\d+(?:[\.,]\d{3})*(?:[\.,]\d{2}))', html_content)
                
                if valores_encontrados:
                    precos_convertidos = []
                    for v in valores_encontrados:
                        # Limpa a string removendo pontos de milhar e padronizando o ponto decimal
                        v_limpo = v.replace('.', '').replace(',', '.')
                        val_float = float(v_limpo)
                        
                        # Filtro de segurança: ignora valores irreais (ex: centavos ou erros de leitura de texto)
                        if val_float > 5.0:
                            precos_convertidos.append(val_float)
                    
                    # Retorna o menor preço (mais em conta) encontrado na listagem da web
                    if precos_convertidos:
                        return min(precos_convertidos)
        except Exception:
            pass
            
        # Caso falhe a conexão ou não ache preços no HTML, recorre ao banco padrão pelo nome do item
        return TABELA_PRECOS_PADRAO.get(nome_item, 50.00)

    st.subheader("📋 Lista de Materiais do Painel (BOM)")
    
    df_editado = st.data_editor(
        st.session_state["componentes"], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_web_orcamento",
        column_order=["id", "Nome", "Marca", "Ampere", "Qtd", "Preco_Unitario"],
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=False),
            "Nome": st.column_config.TextColumn("Nome"),
            "Marca": st.column_config.TextColumn("Marca"),
            "Ampere": st.column_config.TextColumn(
                "Ampere",
                help="Digite a corrente em Ampere do dispositivo"
            ),
            "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, default=1),
            "Preco_Unitario": st.column_config.NumberColumn("Preço", format="R$ %.2f")
        }
    )
    # Atualiza o estado da sessão com as edições manuais feitas nas células
    st.session_state["componentes"] = df_editado

    if st.button("🔍 Sincronizar e Buscar Preços na Web em Tempo Real", type="primary"):
        if df_editado.empty:
            st.warning("Adicione pelo menos uma linha na tabela para buscar preços.")
        else:
            with st.spinner("Varrendo a web em busca do menor preço comercial..."):
                # Cria uma cópia para aplicar as alterações e evitar conflitos de renderização imediata
                df_atualizado = df_editado.copy()
                
                for idx, row in df_atualizado.iterrows():
                    ampere_item = str(row.get("Ampere", ""))
                    nome_item = str(row.get("Nome", ""))
                    
                    # Faz o disparo da busca passando o nome real ("Disjuntor Motor") e o Ampere ("63")
                    menor_preco = buscar_preco_api_aberta(ampere_item, nome_item)
                    
                    # Injeta o valor capturado direto na coluna de Preços da planilha principal
                    df_atualizado.at[idx, "Preco_Unitario"] = menor_preco
                
                # Grava de volta no st.session_state para atualizar a tabela na tela
                st.session_state["componentes"] = df_atualizado
                st.success("Tabela de preços sincronizada com a web com sucesso!")
                st.rerun()

    total_general_painel = 0.0
    linhas_relatorio = []

    for _, row in df_editado.iterrows():
        qtd = pd.to_numeric(row.get("Qtd", 0), errors='coerce')
        if pd.isna(qtd): qtd = 0
        
        p_unit = pd.to_numeric(row.get("Preco_Unitario", 0.0), errors='coerce')
        if pd.isna(p_unit): p_unit = 0.0
        
        subtotal = p_unit * qtd
        total_general_painel += subtotal
        
        id_item = row.get("id", "")
        nome = str(row.get("Nome", "")).strip()
        marca = str(row.get("Marca", "")).strip()
        ampere = str(row.get("Ampere", "")).strip()
        
        # Cria a sequência textual para a coluna Componente
        partes = [p for p in [nome, marca, ampere] if p]
        texto_componente = " - ".join(partes) if partes else "Item"
        
        # Gera o código do componente exatamente igual ao termo enviado para a busca de preço
        texto_codigo = f"{nome} {ampere}".strip() if (nome or ampere) else ""
        
        # Nova estrutura da tabela de relatório ordenado
        linhas_relatorio.append({
            "ID": id_item,
            "Componente": texto_componente,
            "Código": texto_codigo,
            "Quantidade": int(qtd),
            "Preço Unitário": f"R$ {p_unit:,.2f}",
            "Subtotal Comercial": f"R$ {subtotal:,.2f}"
        })

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><h4>Valor de Aquisição de Materiais</h4><h2>R$ {total_general_painel:,.2f}</h2></div>', unsafe_allow_html=True)
    with col2:
        qtd_total = int(pd.to_numeric(df_editado["Qtd"], errors='coerce').fillna(0).sum()) if "Qtd" in df_editado.columns else 0
        st.markdown(f'<div class="metric-box"><h4>Componentes Ativos na Lista</h4><h2>{qtd_total} unidades</h2></div>', unsafe_allow_html=True)

    st.subheader("🛒 Relatório Consolidado para Orçamento Comercial")
    if linhas_relatorio:
        st.dataframe(pd.DataFrame(linhas_relatorio), use_container_width=True)


# ==========================================
# AMBIENTE 2: DIAGRAMA E LAYOUT (AUTOCAD)
# ==========================================
if "2." in ambiente:
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
                if not起源 or not destino: continue
                meio_x = (origem["x"] + destino["x"]) / 2
                xs = [origem["x"], meio_x, meio_x, destino["x"]]
                ys = [origem["y"], origem["y"], destino["y"], destino["y"]]
                cor_plot = mapeamento_cores.get(str(fio.get("cor_fio", "Azul")).strip().lower(), "cyan")
                ax.plot(xs, ys, color=cor_plot, linewidth=2)
                ax.annotate('', xy=(destino["x"], destino["y"]), xytext=(meio_x, destino["y"]), arrowprops=dict(arrowstyle="->", color=cor_plot, lw=1.5))
            except Exception:
                continue

        ax.set_xlim(0, 1000)
        ax.set_ylim(0, 500)
        ax.grid(True, color='#252525', linestyle='--', linewidth=0.5)
        ax.invert_yaxis()
        for spine in ax.spines.values(): spine.set_visible(False)
        st.pyplot(fig)

# ==========================================
# AMBIENTE 3: ASSISTENTE DE IA COOPERATIVO
# ==========================================
if "3." in ambiente:
    st.markdown('<div class="cad-header">🤖 Engenharia Assistida por IA</div>', unsafe_allow_html=True)
    st.info("Módulo de comunicação de IA pausado temporariamente para alinhamento das tabelas comerciais.")
