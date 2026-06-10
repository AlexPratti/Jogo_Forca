import streamlit as st
import unicodedata
import random
import time
import os
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO E CONFIGURAÇÃO
# ==================================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Arena da Forca", page_icon="⚔️", layout="wide")

# --- FUNÇÕES DE APOIO ---
def remover_acentos(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        texto_bruto = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt: texto_bruto.append(txt)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto: texto_bruto.append(txt)
        lista_final = []
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        st.error(f"Erro ao ler o documento Word: {e}")
        return []

# ==================================================
# 2. LOGIN E ESTADO (CORRIGIDO: NÃO ZERA PONTOS AO VOLTAR)
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    nome = st.text_input("Digite seu nome para entrar na Arena:", key="input_nome")
    if st.button("ENTRAR NA ARENA"):
        if nome:
            nome_upper = nome.strip().upper()
            st.session_state.jogador = nome_upper
            
            if nome_upper != "TREINAMENTOWLI":
                # CORREÇÃO: Verifica se o jogador já existia para não zerar os pontos dele
                check_user = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", nome_upper).execute()
                
                if check_user.data:
                    # Jogador já cadastrado: preserva a pontuação existente
                    st.toast(f"👋 Bem-vindo de volta, {nome_upper}! Seus pontos foram mantidos.")
                else:
                    # Jogador novo: inicia com zero pontos
                    supabase.table("forca_disputa_ranking").upsert(
                        {"jogador": nome_upper, "pontos": 0}, 
                        on_conflict="jogador"
                    ).execute()
            st.rerun()
        else:
            st.warning("Por favor, digite um nome.")
    st.stop()
# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def registrar_jogada(letra, jogo_atual):
    # Proteção de segurança otimizada: evita deslogar por oscilações temporárias de rede
    if st.session_state.jogador != "TREINAMENTOWLI":
        try:
            check = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
            if not check.data:
                st.session_state.jogador = None
                st.rerun()
                return
        except Exception:
            # Se houver timeout ou erro de rede, ignora a expulsão e deixa o jogo seguir
            pass

    # Variáveis de controle
    lista_antiga = jogo_atual['letras_tentadas']
    tentadas = [l.strip() for l in lista_antiga.split(",") if l.strip()]
    
    if letra in tentadas:
        return

    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    palavra_alvo = jogo_atual['palavra']
    
    # Lógica de Pontuação por Letra
    if letra in palavra_alvo:
        if st.session_state.jogador != "TREINAMENTOWLI":
            res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
            if res_p.data:
                pts_atuais = res_p.data['pontos']
                supabase.table("forca_disputa_ranking").update({"pontos": pts_atuais + 5}).eq("jogador", st.session_state.jogador).execute()
                st.toast(f"🎯 Boa! +5 pontos pela letra {letra}!")
    else:
        novos_erros += 1
    
    # Atualiza a Arena no Supabase
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()


def reiniciar_arena_completa():
    if "baloes_disparados" in st.session_state:
        del st.session_state.baloes_disparados
    supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
    
    # Busca o modo de jogo atual para mantê-lo ativo mesmo após o reset
    modo_atual = "LIVRE"
    try:
        res = supabase.table("forca_disputa_arena").select("modo_jogo").eq("id", 1).single().execute()
        if res.data and 'modo_jogo' in res.data:
            modo_atual = res.data['modo_jogo']
    except Exception:
        pass

    supabase.table("forca_disputa_arena").update({
        "pergunta": "Aguardando nova pergunta...", "palavra": "ARENA",
        "letras_tentadas": "", "erros": 0, "restantes": 0, "ultimo_jogador": "SISTEMA",
        "modo_jogo": modo_atual
    }).eq("id", 1).execute()
    st.rerun()
# ==================================================
# 4. INTERFACE DA ARENA
# ==================================================

@st.fragment(run_every=2)
def arena_viva():
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Administrador do Jogo iniciar...")
        return

    # TOCA MÚSICA SE O JOGO ESTIVER ATIVO
    if jogo['pergunta'] != "Aguardando nova pergunta..." and jogo['erros'] < 6:
        if os.path.exists("musica.mp3"):
            st.audio("musica.mp3", format="audio/mp3", loop=True, autoplay=True)

    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo.get('erros', 0)
        ultimo_player = jogo.get('ultimo_jogador', "SISTEMA")
        modo_jogo = jogo.get('modo_jogo', "LIVRE")
        
        with c_img:
            nome_img = f"erro{erros_atuais}.png"
            if os.path.exists(nome_img):
                st.image(nome_img, width=180)
            else:
                st.metric("Erros da Equipe", f"{erros_atuais}/6")

        with c_txt:
            contagem = jogo.get('restantes', 0)
            tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
            palavra_alvo = jogo['palavra']
            vitoria = all((letra == " " or letra in tentadas) for letra in palavra_alvo)

            # --- LÓGICA DE PONTUAÇÃO POR PALAVRA ---
            if vitoria and erros_atuais < 6:
                id_palavra_atual = f"vitoria_{palavra_alvo}_{contagem}"
                if id_palavra_atual not in st.session_state:
                    if st.session_state.jogador == ultimo_player and st.session_state.jogador != "TREINAMENTOWLI":
                        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
                        pts = res_p.data['pontos'] if res_p.data else 0
                        supabase.table("forca_disputa_ranking").update({"pontos": pts + 10}).eq("jogador", st.session_state.jogador).execute()
                        st.toast(f"🏆 +10 pontos por vencer o desafio!")
                    st.session_state[id_palavra_atual] = True
                    
            # --- MENSAGENS DE INTERFACE E EMPATE ---
            if (vitoria or erros_atuais >= 6) and contagem == 0:
                rank_final = supabase.table("forca_disputa_ranking").select("*").neq("jogador", "TREINAMENTOWLI").order("pontos", desc=True).execute().data
                if rank_final:
                    max_pts = rank_final[0]['pontos']
                    vencedores = [r['jogador'] for r in rank_final if r['pontos'] == max_pts]
                    nomes = " & ".join(vencedores)
                    st.markdown(f"<h2 style='font-size: 30px;'>🏁 FIM DE JOGO! Vencedor(es): <b>{nomes}</b> com {max_pts} pts</h2>", unsafe_allow_html=True)
                st.error("💀 A ARENA FOI ENCERRADA.")
            else:
                prefixo = f"📝 Pergunta {contagem}" if contagem > 0 else "🔥 PERGUNTA FINAL"
                st.markdown(f"<h3 style='font-size: 24px; margin-bottom: 0px;'>{prefixo}</h3>", unsafe_allow_html=True)
                
                pergunta_texto = jogo['pergunta']
                st.markdown(
                    f"""
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 20px;">
                        <span style="font-size: 22px; color: #004085;">
                            ❓ <b>VALE 5 pts (letra) / 10 pts (vitória):</b> {pergunta_texto}
                        </span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    
            # Palavra oculta
            texto_visual = "".join([f"{l} " if (l == " " or l in tentadas or erros_atuais >= 6) else "_ " for l in palavra_alvo])
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center;">
                    <code style="font-size: 20px; color: #ff4b4b; font-weight: bold;">{texto_visual}</code>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.caption(f"Última jogada por: **{ultimo_player}** | Modo: **{modo_jogo}**")

        # --- LÓGICA DE VALIDAÇÃO DE TURNOS ---
        pode_jogar = True
        mensagem_turno = ""
        
        if modo_jogo == "TURNOS" and ultimo_player != "SISTEMA" and not vitoria and erros_atuais < 6:
            if st.session_state.jogador == ultimo_player and st.session_state.jogador != "TREINAMENTOWLI":
                pode_jogar = False
                mensagem_turno = "⏳ **Aguarde outro jogador fazer uma jogada!** Você não pode jogar duas vezes seguidas."
            else:
                mensagem_turno = f"⚔️ **Sua vez!** O último palpite foi de {ultimo_player}."
        elif modo_jogo == "TURNOS" and ultimo_player == "SISTEMA" and not vitoria and erros_atuais < 6:
            mensagem_turno = "🔥 **Arena aberta!** Qualquer um pode fazer a primeira jogada desta pergunta."

        if mensagem_turno:
            st.info(mensagem_turno)

        # --- CONTROLE DO TECLADO ---
        if not vitoria and erros_atuais < 6:
            if st.session_state.jogador != "TREINAMENTOWLI":
                try:
                    valido = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
                    if not valido.data:
                        st.warning("⚠️ Sua entrada na arena foi revogada pelo Mestre.")
                        if st.button("SAIR", key="btn_sair_arena"):
                            st.session_state.jogador = None
                            st.rerun()
                        st.stop()
                except Exception:
                    pass

            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                # Desativa o botão se a letra já foi usada OU se as regras de turno bloquearem o jogador
                botao_desabilitado = ja_foi or (not pode_jogar)
                
                if cols_tec[i % 9].button(letra, key=f"arena_tec_{letra}", disabled=botao_desabilitado, use_container_width=True):
                    registrar_jogada(letra, jogo)
                    st.rerun()
        elif not (contagem == 0) and vitoria:
             st.info("✅ Palavra correta! Aguardando o Administrador...")

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).execute()
        jogadores_faciais = [r for r in res_rank.data if r['jogador'] != "TREINAMENTOWLI"]
        for i, r in enumerate(jogadores_faciais[:10]):
            st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")

arena_viva()
# ==================================================
# 5. PAINEL DO ADMIN (TREINAMENTOWLI)
# ==================================================
if st.session_state.jogador == "TREINAMENTOWLI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE", expanded=True):
        if "fila_perguntas" not in st.session_state:
            st.session_state.fila_perguntas = []

        col_adm1, col_adm2, col_adm3 = st.columns()
        
        with col_adm1:
            st.markdown("#### 📝 Carregar e Lançar")
            arquivo = st.file_uploader("Arquivo .docx", type=["docx"], key="mestre_upload")
            if st.button("📥 PROCESSAR ARQUIVO"):
                if arquivo:
                    st.session_state.fila_perguntas = extrair_dados_do_docx(arquivo)
                    st.success(f"{len(st.session_state.fila_perguntas)} questões carregadas!")

            if st.button("🚀 LANÇAR PRÓXIMA PERGUNTA", use_container_width=True):
                if st.session_state.fila_perguntas:
                    total_antes = len(st.session_state.fila_perguntas)
                    proxima = st.session_state.fila_perguntas.pop(0)
                    valor_banco = total_antes if len(st.session_state.fila_perguntas) > 1 else 0
                    
                    # Recupera o modo de jogo salvo no banco para mantê-lo ao lançar a próxima
                    res_m = supabase.table("forca_disputa_arena").select("modo_jogo").eq("id", 1).single().execute()
                    modo_atual = res_m.data.get('modo_jogo', 'LIVRE') if res_m.data else 'LIVRE'

                    supabase.table("forca_disputa_arena").update({
                        "pergunta": proxima['pergunta'], "palavra": proxima['resposta'],
                        "letras_tentadas": "", "erros": 0, "restantes": valor_banco,
                        "ultimo_jogador": "SISTEMA", "modo_jogo": modo_atual
                    }).eq("id", 1).execute()
                    st.rerun()
        
        with col_adm2:
            st.markdown("#### 🔄 Arena & Regras")
            st.metric("Na Fila", len(st.session_state.fila_perguntas))
            
            # --- SELETOR DINÂMICO DE MODO DE JOGO ---
            res_arena_modo = supabase.table("forca_disputa_arena").select("modo_jogo").eq("id", 1).single().execute()
            modo_banco = res_arena_modo.data.get('modo_jogo', 'LIVRE') if res_arena_modo.data else 'LIVRE'
            
            index_modo = 0 if modo_banco == "LIVRE" else 1
            novo_modo = st.radio(
                "Alternar Formato de Jogo:",
                ["LIVRE", "TURNOS"],
                index=index_modo,
                help="LIVRE: Todos jogam quando quiserem. TURNOS: Bloqueia o jogador de repetir jogadas seguidas."
            )
            
            if novo_modo != modo_banco:
                supabase.table("forca_disputa_arena").update({"modo_jogo": novo_modo}).eq("id", 1).execute()
                st.toast(f"Modo alterado para: {novo_modo}")
                st.rerun()

            st.write("")
            if st.button("🔄 REINICIAR ARENA", use_container_width=True):
                reiniciar_arena_completa()

        with col_adm3:
            st.markdown("#### 👥 Jogadores")
            if st.button("🗑️ LIMPAR TUDO", use_container_width=True, type="primary"):
                supabase.table("forca_disputa_ranking").delete().neq("jogador", "TREINAMENTOWLI").execute()
                st.rerun()
            
            st.divider()
            res_jogadores = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "TREINAMENTOWLI").execute()
            for j in res_jogadores.data:
                c1, c2 = st.columns()
                c1.caption(j['jogador'])
                if c2.button("❌", key=f"excluir_{j['jogador']}"):
                    supabase.table("forca_disputa_ranking").delete().eq("jogador", j['jogador']).execute()
                    st.rerun()
