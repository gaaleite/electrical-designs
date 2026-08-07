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

# Inicializa o histórico global de orçamentos se não existir
if "historico_orcamentos" not in st.session_state:
    st.session_state["historico_orcamentos"] = {}

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

    def buscar_preco_e_codigo_web(ampere, nome_item):
        preco_padrao = TABELA_PRECOS_PADRAO.get(nome_item, 50.00)
        codigo_padrao = "Código não encontrado (Preço Padrão)"
        
        if not nome_item or str(nome_item).strip() == "":
            return preco_padrao, codigo_padrao
            
        query = f"preço comercial {nome_item} {ampere}".strip()
        url = f"https://duckduckgo.com{urllib.parse.quote(query)}"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
                # Encontra blocos de resultados para associar o preço ao título/código da página
                resultados = re.findall(r'<a class="result__url"[^>]*>([^<]+)</a>.*?R\$\s?(\d+(?:[\.,]\d{3})*(?:[\.,]\d{2}))', html_content, re.DOTALL)
                
                if resultados:
                    precos_validos = []
                    for site, valor in resultados:
                        v_limpo = valor.replace('.', '').replace(',', '.')
                        val_float = float(v_limpo)
                        if val_float > 5.0:
                            # Limpa o domínio do site para servir como o Código/Referência do fornecedor encontrado
                            site_limpo = site.strip().replace("www.", "").split('/')[0]
                            precos_validos.append((val_float, site_limpo))
                    
                    if precos_validos:
                        # Retorna a tupla com o menor preço encontrado e o respectivo domínio/código do site
                        menor_registro = min(precos_validos, key=lambda x: x[0])
                        return menor_registro[0], menor_registro[1]
                        
        except Exception:
            pass
            
        return preco_padrao, codigo_padrao

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
            "Ampere": st.column_config.TextColumn("Ampere", help="Digite a corrente em Ampere"),
            "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, default=1),
            "Preco_Unitario": st.column_config.NumberColumn("Preço", format="R$ %.2f")
        }
    )
    st.session_state["componentes"] = df_editado

    # Inicializa uma coluna oculta para guardar o código raspado da web na sessão se ela não existir
    if "Codigo_Web" not in st.session_state["componentes"].columns:
        st.session_state["componentes"]["Codigo_Web"] = "Não Sincronizado"

    if st.button("🔍 Sincronizar e Buscar Preços na Web em Tempo Real", type="primary"):
        if df_editado.empty:
            st.warning("Adicione pelo menos uma linha na tabela para buscar preços.")
        else:
            with st.spinner("Varrendo a web em busca do menor preço e código comercial..."):
                df_atualizado = df_editado.copy()
                codigos_coletados = []
                
                for idx, row in df_atualizado.iterrows():
                    ampere_item = str(row.get("Ampere", ""))
                    nome_item = str(row.get("Nome", ""))
                    
                    # Retorna o menor preço e a identificação do local onde foi achado
                    menor_preco, codigo_fornecedor = buscar_preco_e_codigo_web(ampere_item, nome_item)
                    
                    df_atualizado.at[idx, "Preco_Unitario"] = menor_preco
                    codigos_coletados.append(codigo_fornecedor)
                
                df_atualizado["Codigo_Web"] = codigos_coletados
                st.session_state["componentes"] = df_atualizado
                st.success("Preços e códigos dos produtos sincronizados com sucesso!")
                st.rerun()

    total_general_painel = 0.0
    linhas_relatorio = []

    for idx, row in df_editado.iterrows():
        qtd = pd.to_numeric(row.get("Qtd", 0), errors='coerce')
        if pd.isna(qtd): qtd = 0
        
        p_unit = pd.to_numeric(row.get("Preco_Unitario", 0.0), errors='coerce')
        if pd.isna(p_unit): p_unit = 0.0
        
        subtotal = p_unit * qtd
        total_general_painel += subtotal
        
        id_item = row.get("id", "")
        nome = str(row.get("Nome", "")).strip()
        marca = str(row.get("Marca", "")).strip()
        
        # Correção 1: Garante a formatação com o "A" caso exista valor de corrente informado
        ampere = str(row.get("Ampere", "")).strip()
        if ampere and not ampere.upper().endswith("A"):
            ampere = f"{ampere}A"
        
        partes = [p for p in [nome, marca, ampere] if p]
        texto_componente = " - ".join(partes) if partes else "Item"
        
        # Correção 2: Puxa o código da página do fornecedor que foi coletado pelo Google/DuckDuckGo
        texto_codigo = row.get("Codigo_Web", "Não Sincronizado") if "Codigo_Web" in df_editado.columns else "Não Sincronizado"
        
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
        df_relatorio_final = pd.DataFrame(linhas_relatorio)
        st.dataframe(df_relatorio_final, use_container_width=True)

    # ==========================================
    # SISTEMA DE SALVAMENTO E BUSCA (HISTÓRICO)
    # ==========================================
    st.markdown("---")
    st.subheader("💾 Gerenciamento e Histórico de Orçamentos")
    
    col_salvar1, col_salvar2 = st.columns([3, 1])
    with col_salvar1:
        nome_orcamento = st.text_input("Identificação / Nome do Orçamento", placeholder="Ex: Orc_Painel_Cliente_A")
    with col_salvar2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Salvar Planilha", use_container_width=True):
            if nome_orcamento.strip() == "":
                st.warning("Insira um nome válido para salvar.")
            elif df_editado.empty:
                st.warning("A planilha atual está vazia.")
            else:
                # Armazena o estado completo atual da planilha e do relatório gerado
                st.session_state["historico_orcamentos"][nome_orcamento] = {
                    "dados_brutos": df_editado.copy(),
                    "relatorio": pd.DataFrame(linhas_relatorio),
                    "total": total_general_painel
                }
                st.success(f"Orçamento '{nome_orcamento}' gravado no histórico!")
                
                # Reseta a planilha original de digitação deixando-a em branco
                st.session_state["componentes"] = pd.DataFrame([{"id": 1, "Nome": "", "Marca": "", "Ampere": "", "Qtd": 1, "Preco_Unitario": 0.0}])
                st.rerun()

    st.markdown("### 🔍 Pesquisar Orçamentos Salvos")
    if st.session_state["historico_orcamentos"]:
        lista_orcamentos = list(st.session_state["historico_orcamentos"].keys())
        orcamento_selecionado = st.selectbox("Selecione um orçamento para carregar ou revisar:", ["-- Selecione --"] + lista_orcamentos)
        
        if orcamento_selecionado != "-- Selecione --":
            dados_salvos = st.session_state["historico_orcamentos"][orcamento_selecionado]
            
            st.write(f"**Valor de Fechamento:** R$ {dados_salvos['total']:,.2f}")
            st.dataframe(dados_salvos["relatorio"], use_container_width=True)
            
            if st.button("🔄 Recuperar e Editar Orçamento Selecionado"):
                st.session_state["componentes"] = dados_salvos["dados_brutos"].copy()
                st.success(f"Dados do orçamento '{orcamento_selecionado}' carregados de volta na planilha superior!")
                st.rerun()
    else:
        st.info("Nenhum orçamento salvo neste histórico até o momento.")



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
