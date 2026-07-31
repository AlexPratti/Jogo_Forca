"use client";

import { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";

export default function ArenaDaForca() {
  const [perfil, setPerfil] = useState<"Jogador" | "Mestre">("Jogador");
  const [jogador, setJogador] = useState<string | null>(null);
  const [senhaInput, setSenhaInput] = useState("");
  const [nomeInput, setNomeInput] = useState("");
  const [erroLogin, setErroLogin] = useState("");
  const [jogo, setJogo] = useState<any>(null);
  const [ranking, setRanking] = useState<any[]>([]);
  const [tempoRestante, setTempoRestante] = useState(15);
  const [abaAtiva, setAbaAtiva] = useState(0);
  useEffect(() => {
    supabase.from("forca_disputa_arena").select("*").eq("id", 1).single().then(({ data }) => { if (data) setJogo(data); });
    supabase.from("forca_disputa_ranking").select("*").order("pontos", { ascending: false }).then(({ data }) => { if (data) setRanking(data); });
    const canalArena = supabase.channel("mudancas_arena").on("postgres_changes", { event: "UPDATE", schema: "public", table: "forca_disputa_arena" }, (p) => setJogo(p.new)).subscribe();
    const canalRanking = supabase.channel("mudancas_ranking").on("postgres_changes", { event: "*", schema: "public", table: "forca_disputa_ranking" }, () => {
      supabase.from("forca_disputa_ranking").select("*").order("pontos", { ascending: false }).then(({ data }) => { if (data) setRanking(data); });
    }).subscribe();
    return () => { supabase.removeChannel(canalArena); supabase.removeChannel(canalRanking); };
  }, []);

  useEffect(() => {
    if (!jogo || jogo.forca_modo_jogo !== "TURNOS") return;
    const intervalo = setInterval(() => {
      if (jogo.forca_timestamp_inicio) {
        const d = Math.floor(Date.now() / 1000) - Math.floor(jogo.forca_timestamp_inicio);
        const r = Math.max(0, jogo.forca_tempo_maximo - d);
        setTempoRestante(r);
        if (r <= 0 && jogo.forca_proximo_turno && jogador === "TREINAMENTOWLI") lidarWithTimeout(jogo.forca_proximo_turno);
      }
    }, 1000);
    return () => clearInterval(intervalo);
  }, [jogo, jogador]);
  const lidarWithTimeout = async (punido: string) => {
    const { data: pData } = await supabase.from("forca_disputa_ranking").select("pontos").eq("jogador", punido).single();
    if (pData) await supabase.from("forca_disputa_ranking").update({ pontos: Math.max(0, pData.pontos - 5) }).eq("jogador", punido);
    const proximo = await calcularProximoTurno(punido);
    await supabase.from("forca_disputa_arena").update({ forca_proximo_turno: proximo, forca_timestamp_inicio: Math.floor(Date.now() / 1000), ultimo_jogador: `SISTEMA (TEMPO DE ${punido} ESGOTOU)` }).eq("id", 1);
  };

  const calcularProximoTurno = async (atual: string) => {
    const { data } = await supabase.from("forca_disputa_ranking").select("jogador").not("jogador", "eq", "TREINAMENTOWLI").order("jogador");
    if (!data || data.length === 0) return "";
    const lista = data.map((r: any) => r.jogador);
    return lista[(lista.indexOf(atual) + 1) % lista.length] || "";
  };

  const realizarLogin = async () => {
    setErroLogin("");
    if (perfil === "Mestre") {
      if (senhaInput.toUpperCase() === "TREINAMENTOWLI") {
        setJogador("TREINAMENTOWLI");
        await supabase.from("forca_disputa_arena").update({ forca_senha_acesso: Math.random().toString(36).substring(2, 6).toUpperCase() }).eq("id", 1);
      } else setErroLogin("Chave de acesso incorreta.");
    } else {
      if (!nomeInput || !senhaInput) return setErroLogin("Preencha todos os campos.");
      const nUpper = nomeInput.trim().toUpperCase();
      const { data: arena } = await supabase.from("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single();
      if (arena && senhaInput.toUpperCase() === arena.forca_senha_acesso.toUpperCase()) {
        setJogador(nUpper);
        const { data: c } = await supabase.from("forca_disputa_ranking").select("*").eq("jogador", nUpper);
        if (!c || c.length === 0) {
          const { count } = await supabase.from("forca_disputa_ranking").select("*", { count: "exact" }).not("jogador", "eq", "TREINAMENTOWLI");
          await supabase.from("forca_disputa_ranking").upsert({ jogador: nUpper, pontos: 0, forca_avatar_num: (count || 0) + 1 });
        }
      } else setErroLogin("Senha incorreta.");
    }
  };
  const registrarJogada = async (letra: string) => {
    if (!jogo || !jogador || jogador === "TREINAMENTOWLI") return;
    if (jogo.forca_modo_jogo === "TURNOS" && jogo.forca_proximo_turno && jogo.forca_proximo_turno !== jogador) return;
    const tentadas = jogo.letras_tentadas ? jogo.letras_tentadas.split(",") : [];
    if (tentadas.includes(letra)) return;
    const novasLetras = jogo.letras_tentadas ? `${jogo.letras_tentadas},${letra}` : letra;
    let novosErros = jogo.erros;
    const palavraAlvo = jogo.palavra || "";
    const { data: pData } = await supabase.from("forca_disputa_ranking").select("pontos").eq("jogador", jogador).single();
    let ptsAtuais = pData ? pData.pontos : 0;
    if (palavraAlvo.includes(letra)) await supabase.from("forca_disputa_ranking").update({ pontos: ptsAtuais + 5 }).eq("jogador", jogador);
    else { novosErros += 1; if (jogo.forca_modo_jogo === "TURNOS") await supabase.from("forca_disputa_ranking").update({ pontos: Math.max(0, ptsAtuais - 5) }).eq("jogador", __ => jogador); }
    const proximo = await calcularProximoTurno(jogador);
    const vitoria = palavraAlvo.split("").every((l: string) => l === " " || [...tentadas, letra].includes(l));
    if (vitoria) await supabase.from("forca_disputa_ranking").update({ pontos: ptsAtuais + 15 }).eq("jogador", jogador);
    await supabase.from("forca_disputa_arena").update({ letras_tentadas: novasLetras, erros: novosErros, ultimo_jogador: jogador, forca_proximo_turno: vitoria ? "" : proximo, forca_timestamp_inicio: Math.floor(Date.now() / 1000) }).eq("id", 1);
  };

  const processarTexto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const leitor = new FileReader();
    leitor.readAsText(e.target.files[0], "UTF-8");
    leitor.onload = async (evento) => {
      try {
        const textoBruto = evento.target?.result as string;
        if (!textoBruto) return;
        const linhas = textoBruto.replace(/\r/g, "").split("\n").map(l => l.trim()).filter(l => l.length > 0);
        const listaFinal: any[] = [];
        
        for (let i = 0; i < linhas.length; i += 2) {
          if (i + 1 < linhas.length) {
            const respLimpa = linhas[i + 1].normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim().replace(/\s+/g, "");
            listaFinal.push({ pergunta: linhas[i], resposta: respLimpa });
          }
        }
        if (listaFinal.length > 0) {
          await supabase.from("forca_disputa_questoes").insert(listaFinal);
          const { count } = await supabase.from("forca_disputa_questoes").select("*", { count: "exact", head: true });
          await supabase.from("forca_disputa_arena").update({ restantes: count || 0 }).eq("id", 1);
          alert(`🎉 Sucesso! ${listaFinal.length} questões carregadas via Texto.`);
          window.location.reload(); // Força a tela a ler o banco atualizado na hora!
        } else alert("⚠️ Nenhuma pergunta encontrada.");
      } catch { alert("⚠️ Erro ao ler o arquivo de perguntas."); }
    };
  };
  const avancarPergunta = async () => {
    const { data: q } = await supabase.from("forca_disputa_questoes").select("*").order("id", { ascending: true }).limit(1);
    if (!q || q.length === 0) return alert("⚠️ Não há perguntas na fila! Carregue um arquivo .txt primeiro.");
    await supabase.from("forca_disputa_questoes").delete().eq("id", q[0].id);
    const { count } = await supabase.from("forca_disputa_questoes").select("*", { count: "exact", head: true });
    await supabase.from("forca_disputa_arena").update({ pergunta: q[0].pergunta, palavra: q[0].resposta, letras_tentadas: "", erros: 0, restantes: count || 0, ultimo_jogador: "SISTEMA", forca_proximo_turno: "", forca_timestamp_inicio: 0 }).eq("id", 1);
  };

  const reiniciarArena = async () => {
    await supabase.from("forca_disputa_questoes").delete().neq("id", 0);
    await supabase.from("forca_disputa_ranking").update({ pontos: 0 }).not("jogador", "eq", "TREINAMENTOWLI");
    await supabase.from("forca_disputa_arena").update({ pergunta: "Aguardando nova pergunta...", palavra: "ARENA", letras_tentadas: "", erros: 0, restantes: 0, ultimo_jogador: "SISTEMA", forca_proximo_turno: "" }).eq("id", 1);
  };

  if (!jogador) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-xl max-w-md w-full shadow-2xl">
          <h1 className="text-3xl font-bold text-center mb-6">⚔️ Arena da Forca</h1>
          <div className="flex gap-4 mb-6 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button className={`flex-1 py-2 rounded-md font-medium transition ${perfil === "Jogador" ? "bg-blue-600 text-white" : "text-slate-400"}`} onClick={() => setPerfil("Jogador")}>Jogador</button>
            <button className={`flex-1 py-2 rounded-md font-medium transition ${perfil === "Mestre" ? "bg-blue-600 text-white" : "text-slate-400"}`} onClick={() => setPerfil("Mestre")}>Mestre (Admin)</button>
          </div>
          {erroLogin && <div className="bg-red-950/50 border border-red-800 text-red-400 p-3 rounded-lg text-sm mb-4">{erroLogin}</div>}
          {perfil === "Jogador" ? (
            <div className="space-y-4">
              <input type="text" placeholder="SEU NOME" className="w-full bg-slate-950 border border-slate-800 p-3 rounded-lg uppercase" value={nomeInput} onChange={e => setNomeInput(e.target.value)} />
              <input type="password" placeholder="SENHA DA ARENA" className="w-full bg-slate-950 border border-slate-800 p-3 rounded-lg" value={senhaInput} onChange={e => setSenhaInput(e.target.value)} />
            </div>
          ) : <input type="password" placeholder="CHAVE ADMIN" className="w-full bg-slate-950 border border-slate-800 p-3 rounded-lg" value={senhaInput} onChange={e => setSenhaInput(e.target.value)} />}
          <button onClick={realizarLogin} className="w-full mt-6 bg-blue-600 p-3 rounded-lg font-bold">ENTRAR NA ARENA</button>
        </div>
      </div>
    );
  }
  if (jogador !== "TREINAMENTOWLI") {
    const tentadas = jogo?.letras_tentadas ? jogo.letras_tentadas.split(",") : [];
    const erros = jogo?.erros || 0;
    const palavra = jogo?.palavra || "";
    const vitoria = palavra.split("").every((l: string) => l === " " || tentadas.includes(l));
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <header className="flex justify-between items-center mb-6 border-b border-slate-800 pb-4">
          <h1 className="text-2xl font-bold">⚔️ Arena da Forca <span className="text-sm bg-blue-950 text-blue-400 px-3 py-1 rounded-full">{jogador}</span></h1>
          {jogo?.forca_modo_jogo === "TURNOS" && <div className="text-right"><p className="font-bold text-amber-400">{jogo.forca_proximo_turno === jogador ? "SUA VEZ!" : jogo.forca_proximo_turno || "Aberto"}</p></div>}
        </header>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between min-h-[400px]">
            <div>
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-lg mb-6">❓ {jogo?.pergunta || "Aguardando o mestre..."}</div>
              <div className="bg-slate-950 p-6 rounded-xl border border-slate-800 flex justify-center tracking-[0.5em] text-3xl font-mono text-red-500 font-bold mb-6">{palavra.split("").map((l: string) => (l === " " ? "  " : tentadas.includes(l) || erros >= 6 ? l : "_")).join("")}</div>
            </div>
            {!vitoria && erros < 6 ? (
              <div className="grid grid-cols-7 sm:grid-cols-13 gap-2">
                {"ABCDEFGHIJKLMNOPQRSTUVWXYZ-".split("").map(letra => {
                  const b = tentadas.includes(letra) || (jogo?.forca_modo_jogo === "TURNOS" && jogo.forca_proximo_turno !== jogador);
                  return <button key={letra} disabled={b} onClick={() => registrarJogada(letra)} className={`p-3 rounded-lg font-bold ${tentadas.includes(letra) ? "bg-slate-800 text-slate-600" : b ? "bg-slate-900 text-slate-700" : "bg-blue-600 text-white"}`}>{letra}</button>;
                })}
              </div>
            ) : <div className="text-center p-4 bg-slate-950 rounded-lg border border-slate-800 text-amber-400 font-bold">{vitoria ? "🎉 Palavra Descoberta!" : "💀 Fim de Jogo!"}</div>}
          </div>
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center"><span className="text-xs font-bold text-slate-400 block mb-2">Erros</span><div className="text-4xl font-black text-red-500">{erros} / 6</div></div>
            {jogo?.forca_modo_jogo === "TURNOS" && <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center"><div className="text-3xl font-mono font-bold text-amber-500">{tempoRestante}s</div></div>}
          </div>
        </div>

        <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">🏆 Placar dos Competidores</h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {ranking.filter((r: any) => r.jogador !== "TREINAMENTOWLI").slice(0, 10).map((r: any, i: number) => (
              <div key={r.jogador} className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col items-center">
                <span className="text-xs font-bold text-slate-500 mb-1">{i + 1}º Lugar</span>
                <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-lg mb-1">👤</div>
                <span className="font-bold text-sm truncate max-w-full text-center">{r.jogador}</span>
                <span className="text-xs text-blue-400">{r.pontos} pts</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <header className="flex justify-between items-center mb-6 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-amber-400">⚔️ Mestre - Arena</h1>
        <div className="bg-slate-900 px-4 py-2 rounded-lg text-sm font-mono">Chave: <span className="text-blue-400 font-bold">{jogo?.forca_senha_acesso}</span></div>
      </header>
      <div className="flex gap-2 border-b border-slate-800 mb-6">
        {["🎮 Arena", "👥 Participantes", "🔄 Configurações"].map((aba, index) => (
          <button key={aba} className={`px-4 py-2 font-medium border-b-2 -mb-[2px] ${abaAtiva === index ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400"}`} onClick={() => setAbaAtiva(index)}>{aba}</button>
        ))}
      </div>
      {abaAtiva === 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 mb-4"><p className="text-slate-300">❓ {jogo?.pergunta}</p></div>
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-center font-mono text-2xl font-bold text-red-400 mb-4">{jogo?.palavra}</div>
            <button onClick={avancarPergunta} className="w-full bg-emerald-600 p-3 rounded-lg font-bold">🚀 LANÇAR PRÓXIMA ({jogo?.restantes || 0} na fila)</button>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            {ranking.filter((r: any) => r.jogador !== "TREINAMENTOWLI").slice(0, 10).map((r: any, i: number) => (
              <div key={r.jogador} className="flex justify-between bg-slate-950 p-2 rounded-lg border border-slate-800 text-sm mb-1"><span>{i+1}º {r.jogador}</span><span className="font-bold text-blue-400">{r.pontos} pts</span></div>
            ))}
          </div>
        </div>
      )}
      {abaAtiva === 1 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-2xl">
          <button onClick={async () => { await supabase.from("forca_disputa_ranking").delete().not("jogador", "eq", "TREINAMENTOWLI"); await supabase.from("forca_disputa_arena").update({ forca_proximo_turno: "" }).eq("id", 1); }} className="bg-red-600 w-full p-2 rounded-lg font-medium text-sm mb-4">🗑️ EXPULSAR TODOS</button>
          {ranking.filter((r: any) => r.jogador !== "TREINAMENTOWLI").map((r: any) => (
            <div key={r.jogador} className="flex justify-between items-center bg-slate-950 p-3 rounded-lg border border-slate-800 mb-1"><span>👤 {r.jogador}</span><button onClick={async () => await supabase.from("forca_disputa_ranking").delete().eq("jogador", r.jogador)} className="bg-red-950 text-red-400 px-3 py-1 rounded-md text-xs">EXPULSAR</button></div>
          ))}
        </div>
      )}
      {abaAtiva === 2 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-xl space-y-6">
          <div><h3 className="text-lg font-bold mb-2">📥 Upload de Perguntas (.txt)</h3><input type="file" accept=".txt" onChange={processarTexto} className="w-full bg-slate-950 border border-slate-800 p-3 rounded-lg text-sm" /></div>
          <div><h3 className="text-lg font-bold mb-2">🔄 Formato</h3><div className="flex gap-4">{["LIVRE", "TURNOS"].map(m => <button key={m} onClick={async () => await supabase.from("forca_disputa_arena").update({ forca_modo_jogo: m, forca_proximo_turno: "" }).eq("id", 1)} className={`flex-1 p-3 rounded-lg font-bold border ${jogo?.forca_modo_jogo === m ? "bg-blue-600 text-white" : "bg-slate-950 text-slate-400"}`}>{m}</button>)}</div></div>
          <button onClick={reiniciarArena} className="w-full bg-slate-950 border border-red-900 text-red-500 p-3 rounded-lg font-bold">🔄 REINICIAR ARENA COMPLETA</button>
        </div>
      )}
    </div>
  );
}
