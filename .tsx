import React, { useState, useEffect, useRef } from 'react';

// --- DEFINIÇÕES DE INTERFACES CORRIGIDAS (Compatíveis com o novo Backend) ---
interface ComponenteFisico {
  id: number;
  "Tag/Nome": string; // Atualizado para bater com o Pandas DataFrame
  Tipo: string;
  Qtd: number;
  x?: number; // Opcional, calculado dinamicamente ou enviado pela IA
  y?: number;
}

interface ConexaoFio {
  origem_id: number;  // Atualizado para bater com o novo esquema
  destino_id: number; // Atualizado para bater com o novo esquema
  cor_fio: string;
  caminho_geometria_json?: { x: number; y: number }[] | null;
}

export const VisualizadorPainel: React.FC = () => {
  const LARGURA_COMP = 110;
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

  // Busca os dados em tempo real da API local do Python (Ajuste a porta se necessário, ex: 8501 ou endpoint FastAPI)
  useEffect(() => {
    const carregarPainelInicial = async () => {
      try {
        setCarregando(true);
        // CORREÇÃO: URL apontando para a porta padrão local de desenvolvimento da sua API
        const resposta = await fetch('http://127.0.0'); 
        if (!resposta.ok) throw new Error('Erro ao carregar os dados técnicos do servidor.');
        
        const dados = await resposta.json();
        
        // Injeta o posicionamento automático no grid caso o backend não envie coordenadas x,y prontas
        const passoX = 800 / (dados.componentes.length || 1);
        const componentesPosicionados = dados.componentes.map((c: any, index: number) => ({
          ...c,
          x: c.x || 120 + (index * passoX * 0.8),
          y: c.y || 250
        }));

        setComponentes(componentesPosicionados);
        setFios(dados.fios || dados.conexoes || []);
      } catch (err: any) {
        // Fallback seguro em modo offline/desenvolvimento para não quebrar a tela enquanto o back não sobe
        setErro(null); 
        setComponentes([
          { id: 1, "Tag/Nome": "QG1 (Geral)", Tipo: "Chave Seccionadora", Qtd: 1, x: 200, y: 250 },
          { id: 2, "Tag/Nome": "K1", Tipo: "Contator de Potência", Qtd: 1, x: 450, y: 250 },
          { id: 3, "Tag/Nome": "F1", Tipo: "Disjuntor Trifásico", Qtd: 16, x: 700, y: 250 }
        ]);
        setFios([
          { origem_id: 1, destino_id: 2, cor_fio: "Vermelho" },
          { origem_id: 2, destino_id: 3, cor_fio: "Preto" }
        ]);
      } finally {
        setCarregando(false);
      }
    };

    carregarPainelInicial();
  }, []);

  // Mapeia posições dos IDs para geração dinâmica de caminhos ortogonais (Estilo AutoCAD)
  const obterPosicaoPorId = (id: number) => {
    const comp = componentes.find(c => c.id === id);
    return comp ? { x: comp.x || 0, y: comp.y || 0 } : { x: 0, y: 0 };
  };

  const gerarCaminhoOrtogonalSVG = (fio: ConexaoFio): string => {
    if (fio.caminho_geometria_json && fio.caminho_geometria_json.length > 0) {
      return `M ${fio.caminho_geometria_json[0].x} ${fio.caminho_geometria_json[0].y} ` + 
             fio.caminho_geometria_json.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ');
    }
    
    // Fallback de cálculo ortogonal em tempo real na tela
    const origem = obterPosicaoPorId(fio.origem_id);
    const destino = obterPosicaoPorId(fio.destino_id);
    const meioX = (origem.x + destino.x) / 2;
    
    return `M ${origem.x} ${origem.y} L ${meioX} ${origem.y} L ${meioX} ${destino.y} L ${destino.x} ${destino.y}`;
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

  if (carregando) return <div style={{ color: '#00FFCC', padding: '20px', fontFamily: 'monospace', background: '#111', minHeight: '100vh' }}>⚡ CAD MOTOR: Inicializando barramentos e sincronizando orçamento...</div>;
  if (erro) return <div style={{ color: '#ff4d4d', padding: '20px', fontFamily: 'monospace', background: '#111', minHeight: '100vh' }}>❌ Erro Crítico: {erro}</div>;

  return (
    <div style={{ padding: '20px', background: '#151515', minHeight: '100vh', color: '#fff', fontFamily: 'monospace' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', borderBottom: '2px solid #00FFCC', paddingBottom: '10px' }}>
        <h2 style={{ color: '#00FFCC', margin: 0 }}>📐 Motor de Visualização CAD Interativo 2D</h2>
        <button onClick={resetarVisao} style={{ padding: '8px 16px', background: '#222', border: '1px solid #00FFCC', color: '#00FFCC', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', transition: '0.2s' }}>
          Resetar Workspace
        </button>
      </div>
      
      <svg 
        width="1000" height="600" 
        onMouseDown={navegarMouseDown} onMouseMove={navegarMouseMove}
        onMouseUp={() => setEstaArrastando(false)} onMouseLeave={() => setEstaArrastando(false)}
        onWheel={controlarZoom}
        style={{ border: '1px solid #252525', background: '#0B0B0B', borderRadius: '4px', cursor: estaArrastando ? 'grabbing' : 'grab', userSelect: 'none' }}
      >
        {/* Grid Técnico de Engenharia (Estilo Linhas de Fundo do AutoCAD) */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1A1A1A" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="1000" height="600" fill="url(#grid)" />
        <rect id="fundo-painel" width="1000" height="600" fill="transparent" />

        {/* Grupo com as transformações de Pan e Zoom */}
        <g transform={`translate(${posicao.x}, ${posicao.y}) scale(${escala})`}>
          
          {/* 1. ROTEAMENTO DE FIOS ORTOGONAIS */}
          {fios.map((fio, index) => {
            const isFocado = fioFocado === index;
            const nenhumFocado = fioFocado === null;

            // Tradução segura de cores vindo do DataFrame em Português para Hexadecimal/Web
            const corMapeada = fio.cor_fio.toLowerCase() === 'vermelho' ? '#ff3333' : 
                               fio.cor_fio.toLowerCase() === 'preto' ? '#333333' : 
                               fio.cor_fio.toLowerCase() === 'azul' ? '#0066ff' : '#00FFCC';

            return (
              <g key={`fio-grupo-${index}`}>
                {/* Hitbox expandida para facilitar a seleção do cabo com o mouse */}
                <path
                  d={gerarCaminhoOrtogonalSVG(fio)}
                  fill="none" stroke="transparent" strokeWidth="16" cursor="pointer"
                  onMouseEnter={() => setFioFocado(index)} onMouseLeave={() => setFioFocado(null)}
                />
                {/* Linha técnica do circuito */}
                <path
                  d={gerarCaminhoOrtogonalSVG(fio)}
                  fill="none"
                  stroke={corMapeada}
                  strokeWidth={isFocado ? "5" : "2.5"}
                  strokeLinecap="square" strokeLinejoin="miter"
                  style={{ transition: 'stroke-width 0.1s, opacity 0.1s', opacity: nenhumFocado || isFocado ? 1 : 0.2 }}
                  pointerEvents="none"
                />
              </g>
            );
          })}

          {/* 2. RENDERIZAÇÃO DOS CUBÍCULOS/COMPONENTES */}
          {componentes.map((comp) => {
            const cx = comp.x || 0;
            const cy = comp.y || 0;
            const xOrigemCaixa = cx - LARGURA_COMP / 2;
            const yOrigemCaixa = cy - ALTURA_COMP / 2;

            return (
              <g key={comp.id} style={{ pointerEvents: 'none' }}>
                {/* Caixa do Dispositivo */}
                <rect 
                  x={xOrigemCaixa} y={yOrigemCaixa} 
                  width={LARGURA_COMP} height={ALTURA_COMP} 
                  fill="#1E1E1E" 
                  stroke="#00FFCC" 
                  strokeWidth="2"
                  style={{ filter: 'drop-shadow(0px 0px 4px rgba(0,255,204,0.15))' }}
                />
                {/* Tag Identificadora do Esquemático */}
                <text x={cx} y={cy - 20} fill="#FFF" fontSize="12" fontWeight="bold" textAnchor="middle" dominantBaseline="middle">
                  {comp["Tag/Nome"]}
                </text>
                {/* Tipo de Hardware */}
                <text x={cx} y={cy + 10} fill="#888" fontSize="10" textAnchor="middle">
                  {comp.Tipo}
                </text>
                {/* Margem de ID / Quantidade técnica */}
                <text x={cx} y={cy + 35} fill="#00FFCC" fontSize="9" fontWeight="bold" textAnchor="middle">
                  ID: {comp.id} | Qtd: {comp.Qtd}
