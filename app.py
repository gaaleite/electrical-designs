import streamlit as st
import os
import matplotlib.pyplot as plt
import json

# 1. Configuração da página OBRIGATORIAMENTE no topo do arquivo
st.set_page_config(page_title="Painel Elétrico - Streamlit", page_icon="⚡", layout="wide")

st.title("⚡ Visualizador Industrial Dinâmico (Streamlit)")
st.markdown("Este app processa a lógica de roteamento e colisão direto na nuvem.")

# --- FUNÇÃO DE LEITURA DO DISCO ---
def ler_json_do_disco(nome_arquivo: str):
    if not os.path.exists(nome_arquivo):
        return []
    try:
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo {nome_arquivo}: {e}")
        return []

# --- CARREGAMENTO DE DADOS ---

# Carrega componentes padrão do repositório
componentes_dados = ler_json_do_disco("componentes.json")
if not componentes_dados:
    componentes_dados = [
        {"id": 45, "nome": "F1 (Origem)", "x": 200, "y": 200},
        {"id": 46, "nome": "K1 (Destino)", "x": 700, "y": 200},
        {"id": 99, "nome": "Disjuntor (Obstáculo)", "x": 450, "y": 200}
    ]

# Upload do arquivo JSON de fios pelo usuário
uploaded_file = st.file_uploader("Carregue o arquivo de leituras (.json)", type=["json"])

fios_dados = []

# Se o usuário subir um arquivo, usamos ele. Caso contrário, tenta ler do disco.
if uploaded_file is not None:
    try:
        fios_dados = json.load(uploaded_file)
        st.success("JSON de fios carregado via upload com sucesso!")
    except json.JSONDecodeError as e:
        st.error(f"Erro de sintaxe no JSON enviado: {e}")
else:
    fios_dados = ler_json_do_disco("leituras.json")

# Se não houver arquivo no upload nem no disco, criamos um mock padrão para não quebrar a tela
if not fios_dados:
    st.info("Nenhum arquivo enviado. Exibindo dados de simulação padrão.")
    fios_dados = [
        {
            "projeto_id": 101, "componente_origem_id": 45, "pino_origem": "2",
            "componente_destino_id": 46, "pino_destino": "1", "bitola_mm2": 2.5, "cor_fio": "Preto"
        },
        {
            "projeto_id": 101, "componente_origem_id": 45, "pino_origem": "4",
            "componente_destino_id": 46, "pino_destino": "3", "bitola_mm2": 1.5, "cor_fio": "Vermelho"
        }
    ]

# --- ALGORITMO DE ROTEAMENTO ---

posicoes_componentes = {c["id"]: {"x": c["x"], "y": c["y"], "nome": c.get("nome", f"Comp {c['id']}")} for c in componentes_dados}

largura_comp = 100
altura_comp = 140
espacamento_fios = 12
resultados_fios = []
historico_rotas = {}

for fio in fios_dados:
    dados = fio.copy()
    origem_id = dados["componente_origem_id"]
    destino_id = dados["componente_destino_id"]
    
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

# --- INTERFACE VISUAL ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Gráfico do Painel Elétrico")
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#111111')
    ax.set_facecolor('#111111')

    # Desenha os componentes na tela
    for c_id, comp in posicoes_componentes.items():
        cor_borda = '#ff4d4d' if c_id == 99 else '#007acc'
        retangulo = plt.Rectangle((comp["x"] - (largura_comp/2), comp["y"] - (altura_comp/2)), 
                                  largura_comp, altura_comp, fill=True, color='#222222', 
                                  edgecolor=cor_borda, linewidth=2, zorder=3)
        ax.add_patch(retangulo)
        ax.text(comp["x"], comp["y"], f"{comp['nome']}\nID: {c_id}", color='white', 
                ha='center', va='center', fontweight='bold', fontsize=9)

    # Desenha os fios processados
    for fio in resultados_fios:
        pontos = fio["caminho_geometria_json"]
        xs = [p["x"] for p in pontos]
        ys = [p["y"] for p in pontos]
        
        cor_fio_str = str(fio.get("cor_fio", "")).lower()
        if "vermelho" in cor_fio_str:
            cor_render = "red"
        elif "preto" in cor_fio_str:
            cor_render = "#444444"  # Um cinza escuro visível no fundo preto do Matplotlib
        else:
            cor_render = "white"
            
        ax.plot(xs, ys, color=cor_render, linewidth=2.5, zorder=2)

    ax.set_xlim(50, 850)
    ax.set_ylim(0, 450)
    ax.axis('off')
    st.pyplot(fig)
    
