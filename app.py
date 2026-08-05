import streamlit as st
import os
import matplotlib.pyplot as plt
import pandas as pd
import json
from google import genai
from google.genai import types

# 1. Configuração da página
st.set_page_config(page_title="Gerador de Projetos Elétricos", page_icon="⚡", layout="wide")

st.title("⚡ Construtor e Roteador Industrial Inteligente")
st.markdown("Crie, edite e simule diagramas elétricos usando planilhas dinâmicas, banco de dados ou IA.")

# --- MOCK DE BANCO DE DADOS (Simulação) ---
@st.cache_data
def carregar_banco_projetos():
    return {
        "Projeto Padrão de Fábrica (ID 101)": {
            "componentes": [
                {"id": 45, "nome": "F1 (Origem)", "x": 200, "y": 200},
                {"id": 46, "nome": "K1 (Destino)", "x": 700, "y": 200},
                {"id": 99, "nome": "Disjuntor (Obstáculo)", "x": 450, "y": 200}
            ],
            "fios": [
                {"componente_origem_id": 45, "pino_origem": "2", "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"},
                {"componente_origem_id": 45, "pino_origem": "4", "componente_destino_id": 46, "pino_destino": "3", "bitola_mm2": 1.5, "cor_fio": "Vermelho"}
            ]
        }
    }

# --- MENU LATERAL DE CONTROLE ---
st.sidebar.header("🛠️ Método de Criação")
metodo = st.sidebar.radio(
    "Escolha como deseja criar o projeto:",
    ["Planilha Escrita (Manual)", "Inteligência Artificial (Prompt)", "Carregar do Banco de Dados"]
)

# Definição dos valores padrão
componentes_dados = [
    {"id": 45, "nome": "F1 (Origem)", "x": 200, "y": 200},
    {"id": 46, "nome": "K1 (Destino)", "x": 700, "y": 200},
    {"id": 99, "nome": "Disjuntor (Obstáculo)", "x": 450, "y": 200}
]
fios_dados = []

# --- VARIÁVEIS DE SESSÃO DA IA ---
if "dados_ia" not in st.session_state:
    st.session_state["dados_ia"] = None

# --- PROCESSAMENTO DOS MÉTODOS DE ENTRADA ---

if metodo == "Planilha Escrita (Manual)":
    st.subheader("📝 Inserção de Dados via Planilha")
    df_inicial = pd.DataFrame([
        {"componente_origem_id": 45, "pino_origem": "2", "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"}
    ])
    df_editado = st.data_editor(df_inicial, num_rows="dynamic", use_container_width=True)
    fios_dados = df_editado.to_dict(orient="records")

elif metodo == "Inteligência Artificial (Prompt)":
    st.subheader("🤖 Assistente de IA para Roteamento")
    prompt_usuario = st.text_area("Descreva o painel:", value="crie um diagrama elétrico com seccionadora e 16 disjuntores", height=100)
    
    if st.button("Gerar Diagrama por IA"):
        api_key_local = st.secrets.get("GEMINI_API_KEY")
        if not api_key_local:
            st.error("❌ Erro: Chave 'GEMINI_API_KEY' não configurada.")
        else:
            with st.spinner("Processando..."):
                try:
                    api_key_local = api_key_local.strip().replace('"', '').replace("'", "")
                    client_local = genai.Client(api_key=api_key_local)
                    
                    esquema_ia = {
                        "type": "OBJECT",
                        "properties": {
                            "componentes": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "id": {"type": "INTEGER"},
                                        "nome": {"type": "STRING"},
                                        "x": {"type": "INTEGER"},
                                        "y": {"type": "INTEGER"}
                                    },
                                    "required": ["id", "nome", "x", "y"]
                                }
                            },
                            "fios": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "componente_origem_id": {"type": "INTEGER"},
                                        "componente_destino_id": {"type": "INTEGER"},
                                        "cor_fio": {"type": "STRING"}
                                    },
                                    "required": ["componente_origem_id", "componente_destino_id", "cor_fio"]
                                }
                            }
                        },
                        "required": ["componentes", "fios"]
                    }

                    response = client_local.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt_usuario,
                        config=types.GenerateContentConfig(
                            system_instruction="Gere componentes industriais e conexões elétricas lógicas entre eles espalhados em X (100-800) e Y (100-400).",
                            response_mime_type="application/json",
                            response_schema=esquema_ia,
                            temperature=0.2
                        ),
                    )
                    st.session_state["dados_ia"] = json.loads(response.text)
                    st.success("🤖 Projeto modelado com sucesso!")
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
                    
    if st.session_state["dados_ia"]:
        componentes_dados = st.session_state["dados_ia"]["componentes"]
        fios_dados = st.session_state["dados_ia"]["fios"]

elif metodo == "Carregar do Banco de Dados":
    st.subheader("🗄️ Projetos Salvos")
    banco = carregar_banco_projetos()
    projeto_selecionado = st.selectbox("Selecione:", list(banco.keys()))
    componentes_dados = banco[projeto_selecionado]["componentes"]
    fios_dados = banco[projeto_selecionado]["fios"]

# --- PROCESSAMENTO DO ALGORITMO DE LOGÍSTICA/ROTEAMENTO ---
posicoes_componentes = {c["id"]: {"x": c["x"], "y": c["y"], "nome": c.get("nome", f"Comp {c['id']}")} for c in componentes_dados}

largura_comp = 80
altura_comp = 100
espacamento_fios = 10
resultados_fios = []
historico_rotas = {}

for fio in fios_dados:
    try:
        origem_id = int(fio["componente_origem_id"])
        destino_id = int(fio["componente_destino_id"])
    except (ValueError, TypeError, KeyError):
        continue
        
    dados = fio.copy()
    origem = posicoes_componentes.get(origem_id, {"x": 100, "y": 100})
    destino = posicoes_componentes.get(destino_id, {"x": 200, "y": 200})
    
    par_chave = tuple(sorted([origem_id, destino_id]))
    id_rota = historico_rotas.get(par_chave, 0)
    historico_rotas[par_chave] = id_rota + 1
    
    deslocamento = id_rota * espacamento_fios
    ponto_intermediario_x = origem["x"] + (destino["x"] - origem["x"]) / 2 + deslocamento
    
    colidiu = False
    obstaculo_pos = None
    for c_id, pos in posicoes_componentes.items():
        if c_id == origem_id or c_id == destino_id:
            continue
        esquerda, direita = pos["x"] - (largura_comp / 2), pos["x"] + (largura_comp / 2)
        topo, base = pos["y"] - (altura_comp / 2), pos["y"] + (altura_comp / 2)
        
        if (esquerda - 15) <= ponto_intermediario_x <= (direita + 15) and (topo - 15) <= origem["y"] <= (base + 15):
            colidiu = True
            obstaculo_pos = pos
            break

    if colidiu and obstaculo_pos:
        y_desvio = obstaculo_pos["y"] - (altura_comp / 2) - 20 - deslocamento
        dados["caminho_geometria_json"] = [
            {"x": origem["x"], "y": origem["y"]},
            {"x": origem["x"] + 20 + deslocamento, "y": origem["y"]},
            {"x": origem["x"] + 20 + deslocamento, "y": y_desvio},
            {"x": destino["x"] - 20 - deslocamento, "y": y_desvio},
            {"x": destino["x"] - 20 - deslocamento, "y": destino["y"]},
            {"x": destino["x"], "y": destino["y"]}
        ]
    else:
        dados["caminho_geometria_json"] = [
            {"x": origem["x"], "y": origem["y"]},
            {"x": ponto_intermediario_x, "y": origem["y"]},
            {"x": ponto_intermediario_x, "y": destino["y"]},
            {"x": destino["x"], "y": destino["y"]}
        ]
        
    resultados_fios.append(dados)

# --- MAPA VISUAL DO PAINEL ELÉTRICO ---
if componentes_dados:
    st.subheader("📊 Gráfico Dinâmico Gerado Real-Time")
    fig, ax = plt.subplots(figsize=(14, 6), facecolor='#111111')
    ax.set_facecolor('#111111')

    for c_id, comp in posicoes_componentes.items():
        retangulo = plt.Rectangle((comp["x"] - (largura_comp/2), comp["y"] - (altura_comp/2)), largura_comp, altura_comp, fill=True, color='#222222', edgecolor='#007acc', linewidth=1.5, zorder=3)
        ax.add_patch(retangulo)
        ax.text(comp["x"], comp["y"], f"{comp['nome']}\nID: {c_id}", color='white', ha='center', va='center', fontweight='bold', fontsize=7)

    for fio in resultados_fios:
        pontos = fio["caminho_geometria_json"]
        xs = [p["x"] for p in pontos]
        ys = [p["y"] for p in pontos]
        cor_fio_str = str(fio.get("cor_fio", "")).lower()
        cor_render = "red" if "vermelho" in cor_fio_str else ("#666666" if "preto" in cor_fio_str else ("#1e90ff" if "azul" in cor_fio_str else "white"))
        ax.plot(xs, ys, color=cor_render, linewidth=1.5, zorder=2)

    ax.set_xlim(50, 850)
    ax.set_ylim(0, 500)
    ax.axis('off')
    st.pyplot(fig)
