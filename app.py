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

# --- BANCO DE DADOS DE MATERIAIS ---
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

# --- INICIALIZAÇÃO DOS ESTADOS DA SESSÃO ---
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
    st.markdown('<div class="cad-header">📊 Engenharia de Materiais & Custos Avançado</div>', unsafe_allow_html=True)
    st.markdown("Insira a marca e o modelo para que o sistema busque e calcule o valor de mercado de cada dispositivo automaticamente.")

    # MOCK EXPANDIDO DE COMPONENTES COM MARCA, MODELO E SEUS PREÇOS REALISTAS
    # Em produção, essa busca seria um 'SELECT preco FROM catalogo_componentes WHERE fabricante = X AND modelo = Y'
    BANCO_PRECOS_COMERCIAIS = {
        ("WEG", "CWM9"): 145.00,
        ("WEG", "MDW-C16"): 22.50,
        ("WEG", "MPW25"): 180.00,
        ("Siemens", "3RT"): 195.00,
        ("Siemens", "5SY"): 38.00,
        ("Schneider", "EasyPact"): 135.00,
        ("Schneider", "Acti9"): 45.00,
        ("Clamper", "VCL"): 110.00
    }

    # Atualiza a estrutura inicial da sessão para conter Marca e Modelo se ainda não existirem
    if "Tag/Nome" in st.session_state["componentes"].columns and "Marca" not in st.session_state["componentes"].columns:
        st.session_state["componentes"] = pd.DataFrame([
            {"id": 1, "Tag/Nome": "QG1 (Geral)", "Tipo": "Chave Seccionadora", "Marca": "WEG", "Modelo": "MPW25", "Qtd": 1},
            {"id": 2, "Tag/Nome": "K1", "Tipo": "Contator de Potência", "Marca": "WEG", "Modelo": "CWM9", "Qtd": 1},
            {"id": 3, "Tag/Nome": "F1", "Tipo": "Disjuntor Trifásico", "Marca": "Siemens", "Modelo": "5SY", "Qtd": 16},
            {"id": 4, "Tag/Nome": "DPS1", "Tipo": "Bloco DPS", "Marca": "Clamper", "Modelo": "VCL", "Qtd": 1}
        ])

    st.subheader("📋 Lista de Materiais do Painel (BOM)")
    
    # Exibe o editor de dados com as novas colunas obrigatórias de busca comercial
    df_editado = st.data_editor(
        st.session_state["componentes"], 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_componentes_comercial"
    )
    st.session_state["componentes"] = df_editado

    # Inicialização das variáveis de cálculo financeiro
    total_painel = 0.0
    itens_cotados = []
    
    # Executa a varredura e busca de preços automática linha por linha
    for _, row in df_editado.iterrows():
        tipo = str(row.get("Tipo", "Genérico"))
        marca = str(row.get("Marca", "")).strip()
        modelo = str(row.get("Modelo", "")).strip()
        qtd = pd.to_numeric(row.get("Qtd", 0), errors='coerce')
        if pd.isna(qtd): 
            qtd = 0
            
        # Tenta buscar o preço exato pela combinação de (Marca, Modelo)
        preco_unit = BANCO_PRECOS_COMERCIAIS.get((marca, modelo))
        
        # Fallback 1: Se não achar o modelo exato, busca um preço médio pela categoria/Tipo
        if preco_unit is None:
            preco_unit = TABELA_PRECOS.get(tipo, 50.00) # R$ 50.00 como taxa padrão se for totalmente novo
            status_preco = "⚠️ Preço Médio Estimado"
        else:
            status_preco = "✅ Preço Comercial Encontrado"
            
        subtotal = preco_unit * qtd
        total_painel += subtotal
        
        itens_cotados.append({
            "Componente": row.get("Tag/Nome", f"Comp_{row.get('id')}"),
            "Marca / Modelo": f"{marca} - {modelo}" if marca and modelo else "Não Informado",
            "Qtd": int(qtd),
            "Preço Unitário": f"R$ {preco_unit:,.2f}",
            "Subtotal": f"R$ {subtotal:,.2f}",
            "Status da Busca": status_preco
        })

    # Painel Dinâmico de Indicadores (Financeiro e Volumetria)
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><h4>Custo Consolidado de Materiais</h4><h2>R$ {total_painel:,.2f}</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><h4>Total de Itens Orçados</h4><h2>{int(df_editado["Qtd"].sum() if "Qtd" in df_editado.columns else 0)} componentes</h2></div>', unsafe_allow_html=True)

    st.subheader("🛒 Relatório de Cotação de Fornecedores")
    if itens_cotados:
        st.dataframe(pd.DataFrame(itens_cotados), use_container_width=True)
    else:
        st.info("Nenhum material adicionado à planilha até o momento.")


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
elif ambiente == "🤖 3. Assistente de IA Cooperativo (RAG/Upload)":
    st.markdown('<div class="cad-header">🤖 Engenharia Assistida por IA</div>', unsafe_allow_html=True)
    projetos_referencia = st.file_uploader("Upload de Projetos Base:", type=["json", "csv", "xlsx"], accept_multiple_files=True)
    
    conteudo_referencia = ""
    if projetos_referencia:
        st.info(f"📂 {len(projetos_referencia)} projeto(s) acoplado(s).")
        for p in projetos_referencia:
            try:
                conteudo_referencia += p.read().decode("utf-8", errors="ignore")[:2000]
            except Exception:
                continue

    prompt_ia = st.text_area("Instruções do novo diagrama:", value="Gere uma malha contendo 1 CLP principal conectado a 3 contatores de motor e proteção por disjuntores industriais.")

    if st.button("Executar Engenharia Cognitiva"):
        api_key_local = st.secrets.get("GEMINI_API_KEY")
        if not api_key_local:
            st.error("❌ Erro: Chave 'GEMINI_API_KEY' ausente nos Secrets.")
        else:
            with st.spinner("Modelando arquitetura elétrica..."):
                try:
                    client_local = genai.Client(api_key=api_key_local.strip())

                    # Estruturação limpa e direta em uma única linha para garantir integridade sintática absoluta
                    esquema_saida = {"type": "OBJECT", "properties": {"componentes": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "INTEGER"}, "Tag/Nome": {"type": "STRING"}, "Tipo": {"type": "STRING"}, "Qtd": {"type": "INTEGER"}}, "required": ["id", "Tag/Nome", "Tipo", "Qtd"]}}, "fios": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"origem_id": {"type": "INTEGER"}, "destino_id": {"type": "INTEGER"}, "cor_fio": {"type": "STRING"}}, "required": ["origem_id", "destino_id", "cor_fio"]}}}, "required": ["componentes", "fios"]}

                    instrucao_sistema = f"Você é um engenheiro de automação. Referências: {conteudo_referencia}. Mapeie a solicitação gerando a estrutura JSON exigida."

                    response = client_local.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=prompt_ia,
                        config=types.GenerateContentConfig(
                            system_instruction=instrucao_sistema,
                            response_mime_type="application/json",
                            response_schema=esquema_saida,
                            temperature=0.1
                        ),
                    )
                    
                    dados_gerados = json.loads(response.text)
                    st.session_state["componentes"] = pd.DataFrame(dados_gerados["componentes"])
                    st.session_state["conexoes"] = pd.DataFrame(dados_gerados["fios"])
                    st.success("🤖 Projeto injetado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha de Execução: {e}")
