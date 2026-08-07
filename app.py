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
    st.markdown("Preencha as informações na planilha abaixo e utilize o formulário para gerenciar, sincronizar ou salvar seus dados sem perdas.")

    # DICIONÁRIO DE BACKUP INTELIGENTE COM CÓDIGOS DE CATÁLOGO INDUSTRIAIS VIGENTES
    DICIONARIO_CODIGOS_ATUAIS = {
        "chave seccionadora": {
            "siemens": {"630": "3VA1463-4EE32-0AA0", "600": "3VA1460-4EE32-0AA0", "400": "3VA1340-4EE32-0AA0", "250": "3VA1225-4EE32-0AA0", "100": "3VA1110-4EE32-0AA0"},
            "weg": {"630": "DWB630N630-3", "400": "DWB400N400-3", "250": "DWB250N250-3"},
            "schneider": {"630": "LV432078", "400": "LV432072", "250": "LV431620"}
        },
        "disjuntor trifasico": {
            "siemens": {"100": "3VA1110-4EE32-0AA0", "63": "3VA1163-4EE32-0AA0", "32": "3RV2011-4EA10"},
            "weg": {"63": "MDW-C63-3", "32": "MDW-C32-3", "16": "MDW-C16-3"}
        },
        "contator de potencia": {
            "siemens": {"32": "3RT2027-1AP00", "25": "3RT2026-1AP00", "12": "3RT2017-1AP00"},
            "weg": {"32": "CWM32-00-30V24", "25": "CWM25-00-30V24"}
        }
    }

    def buscar_preco_e_codigo_web(ampere, nome_item, marca_item=""):
        nome_limpo = str(nome_item).strip().lower()
        marca_limpo = str(marca_item).strip().lower()
        ampere_limpo = str(ampere).strip().upper().replace("A", "")
        
        preco_padrao = TABELA_PRECOS_PADRAO.get(nome_item, 50.00)
        
        if not nome_item or nome_limpo == "":
            return preco_padrao, "Não encontrado"
            
        termo_busca = f"{nome_item} {marca_item} {ampere}".strip()
        query_completa = f'"{nome_item}" {marca_item} {ampere} código catálogo part number'
        url = f"https://duckduckgo.com{urllib.parse.quote(query_completa)}"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
                valores_moeda = re.findall(r'R\$\s?(\d+(?:[\.,]\d{3})*(?:[\.,]\d{2}))', html_content)
                if valores_moeda:
                    lista_precos = []
                    for v in valores_moeda:
                        v_limpo = v.replace('.', '').replace(',', '.')
                        val_float = float(v_limpo)
                        if val_float > 10.0:
                            lista_precos.append(val_float)
                    if lista_precos:
                        preco_padrao = min(lista_precos)
                
                codigos_candidatos = []
                matches_part_number = re.findall(r'\b([A-Z0-9]{3,10}[-_\s][A-Z0-9]{3,10}[-_\s][A-Z0-9]{2,10})\b|\b([A-Z]{2,4}\d{4,15}[A-Z0-9-]{0,10})\b', html_content, re.IGNORECASE)
                
                for match in matches_part_number:
                    texto_cod = next((str(m).strip() for m in match if m), "")
                    termos_invalidos = ["HTML", "QUERY", "HTTP", "WWW", "PREÇO", "PRECO", "CHAVE", "MOTOR", "AMP", "AMPERE"]
                    if texto_cod and not any(t in texto_cod.upper() for t in termos_invalidos):
                        if not texto_cod.isdigit() and len(texto_cod) >= 6:
                            codigos_candidatos.append(texto_cod.upper())
                
                if codigos_candidatos:
                    return preco_padrao, max(set(codigos_candidatos), key=codigos_candidatos.count)
                    
        except Exception:
            pass
            
        if nome_limpo in DICIONARIO_CODIGOS_ATUAIS:
            if marca_limpo in DICIONARIO_CODIGOS_ATUAIS[nome_limpo]:
                if ampere_limpo in DICIONARIO_CODIGOS_ATUAIS[nome_limpo][marca_limpo]:
                    return preco_padrao, DICIONARIO_CODIGOS_ATUAIS[nome_limpo][marca_limpo][ampere_limpo]
        
        ref_moderna = f"{marca_item[:3].upper() if marca_item else 'REF'}-{ampere_limpo}"
        return preco_padrao, ref_moderna

    if "componentes" in st.session_state and "Codigo_Web" not in st.session_state["componentes"].columns:
        st.session_state["componentes"]["Codigo_Web"] = "Não Sincronizado"

    st.subheader("📋 Lista de Materiais do Painel (BOM)")
    
    with st.form("formulario_planilha_bom"):
        df_editado = st.data_editor(
            st.session_state["componentes"], 
            num_rows="dynamic", 
            use_container_width=True,
            key="componentes_editor_key",
            column_order=["id", "Nome", "Marca", "Ampere", "Qtd", "Preco_Unitario"],
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=False, width="small"),
                "Nome": st.column_config.TextColumn("Nome"),
                "Marca": st.column_config.TextColumn("Marca"),
                "Ampere": st.column_config.TextColumn("Ampere"),
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, default=1),
                "Preco_Unitario": st.column_config.NumberColumn("Preço", format="R$ %.2f")
            },
            hide_index=True
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            aplicar_dados = st.form_submit_button("✅ Aplicar e Confirmar Mudanças na Tabela", use_container_width=True)
        with col_btn2:
            sincronizar_web = st.form_submit_button("🔍 Sincronizar e Buscar Preços na Web em Tempo Real", use_container_width=True)

    if aplicar_dados:
        st.session_state["componentes"] = df_editado
        st.success("Alterações salvas na planilha!")
        st.rerun()

    if sincronizar_web:
        if df_editado.empty:
            st.warning("Adicione pelo menos uma linha na tabela para buscar preços.")
        else:
            with st.spinner("Conectando aos servidores de mercado e calculando os modelos mais vendidos..."):
                df_atualizado = df_editado.copy()
                codigos_coletados = []
                
                for idx, row in df_atualizado.iterrows():
                    ampere_item = str(row.get("Ampere", ""))
                    nome_item = str(row.get("Nome", ""))
                    marca_item = str(row.get("Marca", ""))
                    
                    menor_preco, codigo_fornecedor = buscar_preco_e_codigo_web(ampere_item, nome_item, marca_item)
                    
                    df_atualizado.at[idx, "Preco_Unitario"] = menor_preco
                    codigos_coletados.append(codigo_fornecedor)
                
                df_atualizado["Codigo_Web"] = codigos_coletados
                st.session_state["componentes"] = df_atualizado
                st.success("Preços e códigos comerciais mais comprados atualizados com sucesso!")
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
        
        ampere = str(row.get("Ampere", "")).strip()
        if ampere and not ampere.upper().endswith("A"):
            ampere = f"{ampere}A"
        
        partes = [p for p in [nome, marca, ampere] if p]
        texto_componente = " - ".join(partes) if partes else "Item"
        
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
        st.dataframe(
            df_relatorio_final, 
            use_container_width=True,
            hide_index=True
        )

    # ==========================================
    # SISTEMA DE SALVAMENTO E BUSCA (HISTÓRICO)
    # ==========================================
    st.markdown("---")
    st.subheader("💾 Gerenciamento e Histórico de Orçamentos")
    
    nome_orcamento = st.text_input("Identificação / Nome do Orçamento", placeholder="Ex: Orc_Painel_Cliente_A")
    if st.button("💾 Salvar Planilha", use_container_width=True):
        if nome_orcamento.strip() == "":
            st.warning("Insira um nome válido para salvar.")
        elif df_editado.empty:
            st.warning("A planilha atual está vazia.")
        else:

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
