import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Configuração de CORS para permitir a comunicação com o React (.tsx)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELAGEM DOS DADOS (Pydantic) ---
class Ponto(BaseModel):
    x: float
    y: float

class ComponenteFisico(BaseModel):
    id: int
    nome: str
    x: float
    y: float

class ConexaoFio(BaseModel):
    projeto_id: int
    componente_origem_id: int
    componente_destino_id: int
    cor_fio: str
    caminho_geometria_json: Optional[List[Ponto]] = None


# --- FUNÇÕES DE LEITURA DO DISCO ---
def ler_json_do_disco(nome_arquivo: str):
    if not os.path.exists(nome_arquivo):
        return []
    try:
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler o arquivo {nome_arquivo}: {e}")
        return []


# --- ROTAS DA API ---

# ROTA 1: Carrega o painel inicial lendo os dois arquivos JSON e calculando as rotas com desvio
@app.get("/api/painel-inicial")
def obter_painel_inicial():
    componentes_dados = ler_json_do_disco("componentes.json")
    fios_dados = ler_json_do_disco("leituras.json")

    # Criamos um mapa de posições para busca rápida por ID
    posicoes_componentes = {c["id"]: {"x": c["x"], "y": c["y"]} for c in componentes_dados}
    
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
        
        # Algoritmo de Detecção de Colisão em relação ao obstáculo (ID 99 ou qualquer outro no meio)
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
            # Desvio ortogonal por cima do obstáculo
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
            # Rota ortogonal padrão em Z
            caminho = [
                {"x": origem["x"], "y": origem["y"]},
                {"x": ponto_intermediario_x, "y": origem["y"]},
                {"x": ponto_intermediario_x, "y": destino["y"]},
                {"x": destino["x"], "y": destino["y"]}
            ]
            
        dados["caminho_geometria_json"] = caminho
        resultados_fios.append(dados)

    return {
        "componentes": componentes_dados,
        "fios": resultados_fios
    }
