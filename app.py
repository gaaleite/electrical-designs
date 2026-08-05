import streamlit as st
import os
import matplotlib.pyplot as plt
import pandas as pd
import json

# Inicializar cliente do Gemini caso a chave exista
api_key = st.secrets.get("GEMINI_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)


# 1. Configuração da página
st.set_page_config(page_title="Gerador de Projetos Elétricos", page_icon="⚡", layout="wide")

st.title("⚡ Construtor e Roteador Industrial Inteligente")
st.markdown("Crie, edite e simule diagramas elétricos usando planilhas dinâmicas, banco de dados ou IA.")

# --- MOCK DE BANCO DE DADOS (Simulação) ---
@st.cache_data
def carregar_banco_projetos():
    return {
        "Projeto Padrão de Fábrica (ID 101)": [
            {"componente_origem_id": 45, "pino_origem": "2", "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"},
            {"componente_origem_id": 45, "pino_origem": "4", "componente_destino_id": 46, "pino_destino": "3", "bitola_mm2": 1.5, "cor_fio": "Vermelho"}
        ],
        "Projeto de Automação Esteira (ID 102)": [
            {"componente_origem_id": 45, "pino_origem": "1", "componente_destino_id": 99, "pino_destino": "1", "bitola_mm2": 4.0, "cor_fio": "Preto"}
        ]
    }

# --- MENU LATERAL DE CONTROLE (MÉTODOS DE CRIAÇÃO) ---
st.sidebar.header("🛠️ Método de Criação")
metodo = st.sidebar.radio(
    "Escolha como deseja criar o projeto:",
    ["Planilha Escrita (Manual)", "Inteligência Artificial (Prompt)", "Carregar do Banco de Dados"]
)

# Inicialização dos dados dos fios
fios_dados = []

# --- LÓGICA DE ENTRADA DE DADOS CONFIGURADA POR MÉTODOS ---

if metodo == "Planilha Escrita (Manual)":
    st.subheader("📝 Inserção de Dados via Planilha")
    st.markdown("Adicione linhas, digite os IDs dos componentes e configure as conexões diretamente na tabela abaixo:")
    
    # Criamos um DataFrame padrão vazio ou inicial para o usuário preencher
    df_inicial = pd.DataFrame([
        {"componente_origem_id": 45, "pino_origem": "2", "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"}
    ])
    
    # O st.data_editor permite que o usuário edite a planilha online, adicione (+) e delete linhas
    df_editado = st.data_editor(df_inicial, num_rows="dynamic", use_container_width=True)
    fios_dados = df_editado.to_dict(orient="records")

elif metodo == "Inteligência Artificial (Prompt)":
    st.subheader("🤖 Assistente de IA para Roteamento")
    prompt_usuario = st.text_area(
        "Descreva as conexões elétricas que você deseja criar:",
        placeholder="Ex: Conecte o componente 45 (pino 2) ao componente 46 (pino 1) usando um fio preto de 2.5mm."
    )
    
    if st.button("Gerar Diagrama por IA"):
        st.warning("⚠️ Integração com API de IA pendente. (Aqui conectaremos a chave do Gemini/OpenAI para converter o texto em dados estruturados).")
        # Mock simulando o retorno da IA após processar o texto
        fios_dados = [
            {"componente_origem_id": 45, "pino_origem": "2", "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"}
        ]
    else:
        # Mantém vazio até clicar
        fios_dados = []

elif metodo == "Carregar do Banco de Dados":
    st.subheader("🗄️ Projetos Salvos no Banco de Dados")
    banco = carregar_banco_projetos()
    projeto_selecionado = st.selectbox("Selecione o projeto para carregar:", list(banco.keys()))
    fios_dados = banco[projeto_selecionado]
    st.success(f"Projeto '{projeto_selecionado}' carregado com sucesso!")


# --- POSICIONAMENTO FIXO DOS COMPONENTES ---
componentes_dados = [
    {"id": 45, "nome": "F1 (Origem)", "x": 200, "y": 200},
    {"id": 46, "nome": "K1 (Destino)", "x": 700, "y": 200},
    {"id": 99, "nome": "Disjuntor (Obstáculo)", "x": 450, "y": 200}
]
posicoes_componentes = {c["id"]: {"x": c["x"], "y": c["y"], "nome": c.get("nome", f"Comp {c['id']}")} for c in componentes_dados}

largura_comp = 100
altura_comp = 140
espacamento_fios = 12
resultados_fios = []
historico_rotas = {}

# --- ALGORITMO DE ROTEAMENTO (Executa os dados gerados acima) ---
if fios_dados:
    for fio in fios_dados:
        # Validação simples para evitar quebras se o usuário deixar campos em branco na planilha
        try:
            origem_id = int(fio["componente_origem_id"])
            destino_id = int(fio["componente_destino_id"])
        except (ValueError, TypeError, KeyError):
            continue # Pula linhas inválidas ou incompletas
            
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
            y_desvio = obstaculo_pos["y"] - (altura_comp / 2) - 30 - deslocamento
            caminho = [
                {"x": origem["x"], "y": origem["y"]},
                {"x": origem["x"] + 30 + deslocamento, "y": origem["y"]},
                {"x": origem["x"] + 30 + deslocamento, "y": y_desvio},
                {"x": destino["x"] - 30 - deslocamento, "y": y_desvio},
                {"x": destino["x"] - 30 - deslocamento, "y": destino["y"]},
                {"x": destino["x"], "y": destino["y"]}
            ]
        else:
            caminho = [
                {"x": origem["x"], "y": origem["y"]},
                {"x": ponto_intermediario_x, "y": origem["y"]},
                {"x": ponto_intermediario_x, "y": destino["y"]},
                {"x": destino["x"], "y": destino["y"]}
            ]
            
        dados["caminho_geometria_json"] = caminho
        resultados_fios.append(dados)

# --- RENDERIZAÇÃO GRÁFICA DO DIAGRAMA ---
if resultados_fios:
    st.subheader("📊 Gráfico Dinâmico Gerado Real-Time")
    fig, ax = plt.subplots(figsize=(12, 5), facecolor='#111111')
    ax.set_facecolor('#111111')

    # Desenha os componentes
    for c_id, comp in posicoes_componentes.items():
        cor_borda = '#ff4d4d' if c_id == 99 else '#007acc'
        retangulo = plt.Rectangle((comp["x"] - (largura_comp/2), comp["y"] - (altura_comp/2)), 
                                  largura_comp, altura_comp, fill=True, color='#222222', 
                                  edgecolor=cor_borda, linewidth=2, zorder=3)
        ax.add_patch(retangulo)
        ax.text(comp["x"], comp["y"], f"{comp['nome']}\nID: {c_id}", color='white', 
                ha='center', va='center', fontweight='bold', fontsize=9)

    # Desenha os fios baseados na tabela/método selecionado
    for fio in resultados_fios:
        pontos = fio["caminho_geometria_json"]
        xs = [p["x"] for p in pontos]
        ys = [p["y"] for p in pontos]
        
        cor_fio_str = str(fio.get("cor_fio", "")).lower()
        if "vermelho" in cor_fio_str:
            cor_render = "red"
        elif "preto" in cor_fio_str:
            cor_render = "#555555" # Cinza visível para simular preto no fundo escuro
        elif "azul" in cor_fio_str:
            cor_render = "#1e90ff"
        else:
            cor_render = "white"
            
        ax.plot(xs, ys, color=cor_render, linewidth=2.5, zorder=2)

    ax.set_xlim(50, 850)
    ax.set_ylim(0, 450)
    ax.axis('off')
    st.pyplot(fig)
else:
    st.info("Insira ou carregue dados válidos para gerar o diagrama visual.")
