import streamlit as st
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA PROFISSIONAL
# ==========================================
st.set_page_config(
    page_title="Deigners Elétricos", 
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

st.title("⚡ Planilhas e Diagramas Elétricos Industriais")

# --- BANCO DE PREÇOS AUXILIAR (FALLBACK DE SEGURANÇA) ---
TABELA_PRECOS_PADRAO = {
    "disjuntor caixa moldada": 5200.00,
    "chave seccionadora": 1650.00,
    "disjuntor motor": 280.00,
    "disjuntor": 120.00,
    "contatora": 350.00,
    "barramento de cobre": 450.00,
    "clp industrial": 2500.00,
    "relé térmico de sobrecarga": 180.00
}

# --- DICIONÁRIO DE CÓDIGOS VIGENTES ---
DICIONARIO_CODIGOS_ATUAIS = {
    "chave seccionadora": {
        "siemens": {"630": "S326303", "600": "S326303", "400": "S324003", "250": "S322503", "100": "S321003"},
        "weg": {"630": "FSW630-3P", "400": "FSW400-3P", "250": "FSW250-3P"},
        "schneider": {"630": "INS630-LV431548", "400": "INS400-LV431540", "250": "INS431100"}
    },
    "disjuntor caixa moldada": {
        "siemens": {"630": "3VA1463-4EE32-0AA0", "600": "3VA1460-4EE32-0AA0", "500": "3VA1450-4EE32-0AA0", "400": "3VA1340-4EE32-0AA0", "250": "3VA1225-4EE32-0AA0", "100": "3VA1110-4EE32-0AA0"},
        "weg": {"630": "DWB630N630-3", "500": "DWB500N500-3", "400": "DWB400N400-3", "250": "DWB250N250-3"},
        "schneider": {"630": "LV432078", "400": "LV432072", "250": "LV431620"}
    },
    "disjuntor": {
        "siemens": {"100": "3VA1110-4EE32-0AA0", "63": "3VA1163-4EE32-0AA0", "32": "3RV2011-4EA10"},
        "weg": {"63": "MDW-C63-3", "32": "MDW-C32-3"}
    },
    "contatora": {
        "siemens": {"32": "3RT2027-1AP00", "25": "3RT2026-1AP00"},
        "weg": {"32": "CWM32-00-30V24"}
    }
}

# --- FUNÇÃO DE CONVERSÃO DE DATAFRAME PARA XML ---
def converter_df_para_xml(df: pd.DataFrame, root_element: str = "ListaDeMateriais", item_element: str = "Componente") -> str:
    """Converte um DataFrame do pandas em uma string formatada em XML."""
    root = ET.Element(root_element)
    for _, row in df.iterrows():
        item = ET.SubElement(root, item_element)
        for col in df.columns:
            child = ET.SubElement(item, str(col).replace(" ", "_"))
            val = str(row[col]) if pd.notna(row[col]) and row[col] is not None else ""
            child.text = val
    
    xml_bruto = ET.tostring(root, encoding="utf-8")
    xml_formatado = minidom.parseString(xml_bruto).toprettyxml(indent="  ")
    return xml_formatado

# --- INICIALIZAÇÃO DOS ESTADOS DA SESSÃO ---
if "componentes" not in st.session_state:
    st.session_state["componentes"] = pd.DataFrame(
        columns=["id", "Nome", "Marca", "Ampere", "Qtd", "Preco_Unitario", "Codigo_Web"]
    )

if "conexoes" not in st.session_state:
    st.session_state["conexoes"] = pd.DataFrame(
        columns=["origem_id", "destino_id", "cor_fio"]
    )

if "historico_orcamentos" not in st.session_state:
    st.session_state["historico_orcamentos"] = {}

if "Codigo_Web" not in st.session_state["componentes"].columns:
    st.session_state["componentes"]["Codigo_Web"] = ""

# --- NAVEGAÇÃO ---
st.sidebar.header("🕹️ Centro de Operações")
ambiente = st.sidebar.radio(
    "Mudar ambiente de trabalho:",
    [
        "📊 1. Orçamento",
        "📐 2. Diagrama e Layout",
        "🤖 3. Assistente de IA Cooperativo"
    ]
)

mapeamento_cores = {
    "preto": "black", "azul": "blue", "vermelho": "red", 
    "verde": "green", "amarelo": "gold", "cinza": "gray"
}

# ==========================================
# AMBIENTE 1: ORÇAMENTO
# ==========================================
if "1." in ambiente:
    st.markdown('<div class="cad-header">📊 Engenharia de Materiais & Orçamento Web Real-Time</div>', unsafe_allow_html=True)
    st.markdown("Preencha as informações na planilha abaixo e utilize os botões para confirmar ou sincronizar os preços.")

    def buscar_preco_e_codigo_web(ampere, nome_item, marca_item=""):
        nome_limpo = str(nome_item).strip().lower()
        marca_limpo = str(marca_item).strip().lower()
        ampere_limpo = str(ampere).strip().upper().replace("A", "")
        
        preco_padrao = TABELA_PRECOS_PADRAO.get(nome_limpo, 150.00)
        
        if not nome_item or nome_limpo == "" or nome_limpo == "none":
            return 0.0, "Não encontrado"
            
        query_completa = f'"{nome_item}" {marca_item} {ampere} preco comprar'
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query_completa)}"
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
                valores_moeda = re.findall(r'R\$\s?(\d+(?:[\.,]\d{3})*(?:[\.,]\d{2}))', html_content)
                if valores_moeda:
                    lista_precos = []
                    for v in valores_moeda:
                        v_limpo = v.replace('.', '').replace(',', '.')
                        val_float = float(v_limpo)
                        if "caixa moldada" in nome_limpo or "seccionadora" in nome_limpo:
                            if val_float > 400.0:
                                lista_precos.append(val_float)
                        else:
                            if val_float > 10.0:
                                lista_precos.append(val_float)
                    if lista_precos:
                        preco_padrao = min(lista_precos)
                
                codigos_candidatos = []
                matches_part_number = re.findall(r'\b(3VA\d{4,15}[A-Z0-9-]*)\b|\b(S32\d{3,6})\b|\b(FSW\d{3}[A-Z0-9-]*)\b|\b([A-Z0-9]{4,10}[-_\s][A-Z0-9]{4,10})\b', html_content, re.IGNORECASE)
                
                for match in matches_part_number:
                    texto_cod = next((str(m).strip() for m in match if m), "")
                    termos_invalidos = ["HTML", "QUERY", "HTTP", "WWW", "PREÇO", "PRECO", "AMP", "AMPERE"]
                    if texto_cod and not any(t in texto_cod.upper() for t in termos_invalidos):
                        if not texto_cod.isdigit() and len(texto_cod) >= 5:
                            codigos_candidatos.append(texto_cod.upper())
                
                if codigos_candidatos:
                    return preco_padrao, max(set(codigos_candidatos), key=codigos_candidatos.count)
        except Exception:
            pass
            
        codigo_final = f"{marca_item[:3].upper() if marca_item else 'REF'}-{ampere_limpo}"
        if nome_limpo in DICIONARIO_CODIGOS_ATUAIS:
            if marca_limpo in DICIONARIO_CODIGOS_ATUAIS[nome_limpo]:
                if ampere_limpo in DICIONARIO_CODIGOS_ATUAIS[nome_limpo][marca_limpo]:
                    codigo_final = DICIONARIO_CODIGOS_ATUAIS[nome_limpo][marca_limpo][ampere_limpo]
        
        return preco_padrao, codigo_final

    st.subheader("📋 Lista de Materiais do Painel (BOM)")
    
    with st.form("formulario_planilha_bom"):
        df_editado = st.data_editor(
            st.session_state["componentes"], 
            num_rows="dynamic", 
            use_container_width=True,
            key="componentes_editor_key",
            column_order=["id", "Nome", "Marca", "Ampere", "Qtd", "Preco_Unitario", "Codigo_Web"],
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=False, width="small"),
                "Nome": st.column_config.TextColumn("Nome"),
                "Marca": st.column_config.TextColumn("Marca"),
                "Ampere": st.column_config.TextColumn("Ampere"),
                "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, default=1),
                "Preco_Unitario": st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f", default=0.0),
                "Codigo_Web": st.column_config.TextColumn("Código Fornecedor / Web")
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
        if df_editado.empty or df_editado.dropna(how="all").empty:
            st.warning("Adicione pelo menos um item na tabela para buscar preços.")
        else:
            with st.spinner("Conectando aos servidores de mercado e buscando preços/códigos comerciais..."):
                df_atualizado = df_editado.copy()
                codigos_coletados = []
                
                for idx, row in df_atualizado.iterrows():
                    ampere_item = str(row.get("Ampere", ""))
                    nome_item = str(row.get("Nome", ""))
                    marca_item = str(row.get("Marca", ""))
                    preco_atual = row.get("Preco_Unitario")
                    
                    if not nome_item or str(nome_item).strip() == "" or str(nome_item).strip().lower() == "none":
                        codigos_coletados.append("")
                        continue

                    menor_preco, codigo_fornecedor = buscar_preco_e_codigo_web(ampere_item, nome_item, marca_item)
                    
                    # Atualiza o preço unitário sempre que estiver None, NaN ou 0.0
                    if pd.isna(preco_atual) or preco_atual is None or float(preco_atual or 0) == 0.0:
                        df_atualizado.at[idx, "Preco_Unitario"] = float(menor_preco)
                        
                    codigos_coletados.append(codigo_fornecedor)
                
                df_atualizado["Codigo_Web"] = codigos_coletados
                st.session_state["componentes"] = df_atualizado
                st.success("Preços e códigos comerciais atualizados com sucesso!")
                st.rerun()

    # --- RESUMO FINANCEIRO E DOWNLOAD XML ---
    st.markdown("---")
    col_fin1, col_fin2, col_export = st.columns([1, 1, 1])

    total_geral_painel = 0.0
    for idx, row in st.session_state["componentes"].iterrows():
        try:
            qtd = float(row.get("Qtd") or 0)
            preco = float(row.get("Preco_Unitario") or 0.0)
            total_geral_painel += (qtd * preco)
        except (ValueError, TypeError):
            pass

    with col_fin1:
        st.metric("Total de Componentes", len(st.session_state["componentes"].dropna(subset=["Nome"])))
    with col_fin2:
        st.metric("Custo Total Estimado (BOM)", f"R$ {total_geral_painel:,.2f}")
    
    with col_export:
        st.markdown("**💾 Exportar Projeto**")
        df_para_exportar = st.session_state["componentes"]
        
        if not df_para_exportar.empty:
            xml_string = converter_df_para_xml(df_para_exportar, root_element="ProjetoPainelEletrico", item_element="Componente")
            
            st.download_button(
                label="📥 Baixar Planilha em XML",
                data=xml_string,
                file_name="lista_materiais_painel.xml",
                mime="application/xml",
                use_container_width=True
            )
        else:
            st.info("Insira dados na tabela para habilitar o download em XML.")

# ==========================================
# AMBIENTE 2: DIAGRAMA E LAYOUT
# ==========================================
if "2." in ambiente:
    st.markdown('<div class="cad-header">📐 Canvas de Roteamento (Visualização CAD)</div>', unsafe_allow_html=True)
    col_config, col_canvas = st.columns([1, 2])
    
    with col_config:
        st.subheader("⚡ Conexões dos Fios")
        df_fios = st.data_editor(st.session_state["conexoes"], num_rows="dynamic", use_container_width=True, key="editor_fios")
        st.session_state["conexoes"] = df_fios
        
        if not df_fios.empty:
            xml_fios = converter_df_para_xml(df_fios, root_element="ConexoesEletricas", item_element="Fio")
            st.download_button(
                label="📥 Baixar Diagrama de Fios (.XML)",
                data=xml_fios,
                file_name="conexoes_fios.xml",
                mime="application/xml",
                use_container_width=True
            )
        
    with col_canvas:
        st.subheader("🖥️ Esquemático Unifilar / Trifilar")
        comp_df = st.session_state["componentes"].dropna(subset=["id"])
        
        if comp_df.empty:
            st.warning("Nenhum componente cadastrado. Vá até a aba '1. Dimensionamento e Orçamento' e insira componentes na tabela.")
        else:
            posicoes = {}
            num_comp = len(comp_df)
            passo_x = 800 / (num_comp if num_comp > 0 else 1)
            
            for i, (_, row) in enumerate(comp_df.iterrows()):
                c_id = row.get("id")
                if pd.isna(c_id): 
                    continue
                posicoes[int(c_id)] = {
                    "x": 100 + (i * passo_x * 0.8), 
                    "y": 250, 
                    "nome": str(row.get("Nome", f"ID {c_id}"))
                }

            fig, ax = plt.subplots(figsize=(11, 6), facecolor='#151515')
            ax.set_facecolor('#151515')
            largura_box, altura_box = 100, 80
            
            for c_id, pos in posicoes.items():
                rect = plt.Rectangle((pos["x"] - largura_box/2, pos["y"] - altura_box/2), largura_box, altura_box, facecolor='#2A2A2A', edgecolor='#00FFCC', linewidth=2)
                ax.add_patch(rect)
                ax.text(pos["x"], pos["y"], f"ID {c_id}\n{pos['nome']}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
                
            for _, fio in df_fios.iterrows():
                try:
                    origem_id = int(fio["origem_id"]) if pd.notna(fio["origem_id"]) else None
                    destino_id = int(fio["destino_id"]) if pd.notna(fio["destino_id"]) else None
                    
                    origem = posicoes.get(origem_id)
                    destino = posicoes.get(destino_id)
                    
                    if not origem or not destino: 
                        continue
                        
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
            for spine in ax.spines.values(): 
                spine.set_visible(False)
            st.pyplot(fig)

# ==========================================
# AMBIENTE 3: ASSISTENTE DE IA COOPERATIVO
# ==========================================
if "3." in ambiente:
    st.markdown('<div class="cad-header">🤖 Engenharia Assistida por IA</div>', unsafe_allow_html=True)
    st.info("Módulo de comunicação de IA pausado temporariamente para alinhamento das tabelas comerciais.")
