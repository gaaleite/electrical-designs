import React, { useState, useEffect, useRef } from 'react';

// --- DEFINIÇÕES DE INTERFACES (TypeScript) ---
interface Ponto { 
  x: number; 
  y: number; 
}

interface ConexaoFio {
  projeto_id: number;
  componente_origem_id: number;
  componente_destino_id: number;
  cor_fio: string;
  caminho_geometria_json: Ponto[] | null;
}

interface ComponenteFisico {
  id: number;
  nome: string;
  x: number;
  y: number;
}

export const VisualizadorPainel: React.FC = () => {
  const LARGURA_COMP = 100;
  const ALTURA_COMP = 140;

  // Estados de Dados da API
  const [componentes, setComponentes] = useState<ComponenteFisico[]>([]);
  const [fios, setFios] = useState<ConexaoFio[]>([]);
  const [carregando, setCarregando] = useState<boolean>(true);
  const [erro, setErro] = useState<string | null>(null);

  // Estados de Interatividade (Zoom, Pan e Hover)
  const [escala, setEscala] = useState<number>(1);
  const [posicao, setPosicao] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [estaArrastando, setEstaArrastando] = useState<boolean>(false);
  const [fioFocado, setFioFocado] = useState<number | null>(null);
  
  const arrastoInicio = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Busca a estrutura inicial do backend (que lê os arquivos .json do disco)
  useEffect(() => {
    const carregarPainelInicial = async () => {
      try {
        setCarregando(true);
        const resposta = await fetch('http://127.0.0');
        if (!resposta.ok) throw new Error('Erro ao carregar o painel do servidor.');
        
        const dados = await resposta.json();
        setComponentes(dados.componentes);
        setFios(dados.fios);
      } catch (err: any) {
        setErro(err.message || 'Erro de conexão com a API.');
      } finally {
        setCarregando(false);
      }
    };

    carregarPainelInicial();
  }, []);

  const gerarCaminhoSVG = (pontos: Ponto[] | null): string => {
    if (!pontos || pontos.length === 0) return '';
    const [inicio, ...resto] = pontos;
    return `M ${inicio.x} ${inicio.y} ` + resto.map(p => `L ${p.x} ${p.y}`).join(' ');
  };

  // Funções de controle do Mouse (Pan/Arrastar a tela)
  const navegarMouseDown = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    if ((e.target as SVGElement).tagName === 'svg' || (e.target as SVGElement).id === 'fundo-painel') {
      setEstaArrastando(true);
      arrastoInicio.current = { x: e.clientX - posicao.x, y: e.clientY - posicao.y };
    }
  };

  const navegarMouseMove = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    if (!estaArrastando) return;
    setPosicao({ x: e.clientX - arrastoInicio.current.x, y: e.clientY - arrastoInicio.current.y });
  };

  const controlarZoom = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const fatorZoom = e.deltaY < 0 ? 1.1 : 0.9;
    setEscala(antiga => Math.max(0.2, Math.min(4, antiga * fatorZoom)));
  };

  const resetarVisao = () => {
    setEscala(1);
    setPosicao({ x: 0, y: 0 });
  };

  if (carregando) return <div style={{ color: '#fff', padding: '20px', fontFamily: 'sans-serif' }}>⚡ Conectando ao backend e calculando rotas...</div>;
  if (erro) return <div style={{ color: '#ff4d4d', padding: '20px', fontFamily: 'sans-serif' }}>❌ Erro: {erro}</div>;

  return (
    <div style={{ padding: '20px', background: '#222', minHeight: '100vh', color: '#fff', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
        <h2>Painel Industrial Dinâmico (Arquivos JSON + Anti-Colisão)</h2>
        <button onClick={resetarVisao} style={{ padding: '8px 16px', background: '#007acc', border: 'none', color: '#fff', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
          Resetar Visão
        </button>
      </div>
      
      <svg 
        width="1000" height="600" 
        onMouseDown={navegarMouseDown} onMouseMove={navegarMouseMove}
        onMouseUp={() => setEstaArrastando(false)} onMouseLeave={() => setEstaArrastando(false)}
        onWheel={controlarZoom}
        style={{ border: '2px solid #444', background: '#111', borderRadius: '8px', cursor: estaArrastando ? 'grabbing' : 'grab', userSelect: 'none' }}
      >
        {/* Fundo invisível para capturar o clique do arrastar */}
        <rect id="fundo-painel" width="1000" height="600" fill="transparent" />

        {/* Grupo que aplica as transformações globais de Pan e Zoom */}
        <g transform={`translate(${posicao.x}, ${posicao.y}) scale(${escala})`}>
          
          {/* 1. FIOS (RENDERIZADOS PRIMEIRO PARA FICAREM ATRÁS DAS CAIXAS) */}
          {fios.map((fio, index) => {
            const isFocado = fioFocado === index;
            const nenhumFocado = fioFocado === null;

            // Tratamento básico para cores vindo em português do JSON
            const corFinal = fio.cor_fio.toLowerCase() === 'vermelho' ? '#ff3333' : 
                             fio.cor_fio.toLowerCase() === 'preto' ? '#ffffff' : fio.cor_fio;

            return (
              <g key={`fio-grupo-${index}`}>
                {/* Linha invisível maior (Hitbox) para capturar o mouse facilmente */}
                <path
                  d={gerarCaminhoSVG(fio.caminho_geometria_json)}
                  fill="none" stroke="transparent" strokeWidth="15" cursor="pointer"
                  onMouseEnter={() => setFioFocado(index)} onMouseLeave={() => setFioFocado(null)}
                />
                {/* Linha visual real */}
                <path
                  d={gerarCaminhoSVG(fio.caminho_geometria_json)}
                  fill="none"
                  stroke={corFinal}
                  strokeWidth={isFocado ? "6" : "3"}
                  strokeLinecap="round" strokeLinejoin="round"
                  style={{ transition: 'stroke-width 0.15s, opacity 0.15s', opacity: nenhumFocado || isFocado ? 1 : 0.25 }}
                  pointerEvents="none"
                />
              </g>
            );
          })}

          {/* 2. COMPONENTES (CAIXAS) */}
          {componentes.map((comp) => {
            const xOrigemCaixa = comp.x - LARGURA_COMP / 2;
            const yOrigemCaixa = comp.y - ALTURA_COMP / 2;
            const ehObstaculo = comp.id === 99;

            return (
              <g key={comp.id} style={{ pointerEvents: 'none' }}>
                <rect 
                  x={xOrigemCaixa} y={yOrigemCaixa} 
                  width={LARGURA_COMP} height={ALTURA_COMP} 
                  fill="#333" 
                  stroke={ehObstaculo ? "#ff4d4d" : "#007acc"} 
                  strokeWidth="2" rx="6" 
                />
                <text x={comp.x} y={comp.y} fill="#fff" fontSize="13" fontWeight="bold" textAnchor="middle" dominantBaseline="middle">
                  {comp.nome}
                </text>
                <text x={comp.x} y={comp.y + 25} fill="#888" fontSize="11" textAnchor="middle">
                  ID: {comp.id}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <p style={{ color: '#888', fontSize: '13px', marginTop: '10px' }}>💡 Dica: Role o scroll sobre o painel para dar <b>Zoom</b>. Clique e arraste no fundo preto para <b>Mover</b> a tela.</p>
    </div>
  );
};

export default VisualizadorPainel;
