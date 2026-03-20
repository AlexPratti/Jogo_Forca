import streamlit as st
import unicodedata
import random
import time
import os
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO E CONFIGURAÇÃO (APENAS UMA VEZ)
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
# 2. LOGIN E ESTADO (VERSÃO COM TRAVA DE ADMIN)
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
            
            # --- ALTERAÇÃO AQUI ---
            # Só registra no banco de dados se o nome NÃO for o seu
            if nome_upper != "PRATTI":
                supabase.table("forca_disputa_ranking").upsert(
                    {"jogador": nome_upper, "pontos": 0}, 
                    on_conflict="jogador"
                ).execute()
            # ----------------------
            
            st.rerun()
        else:
            st.warning("Por favor, digite um nome.")
    st.stop()


# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def registrar_jogada(letra, jogo_atual):
    # --- NOVA TRAVA DE SEGURANÇA ---
    # Verifica se o jogador ainda existe no banco (ou se é o Admin Pratti)
    if st.session_state.jogador != "PRATTI":
        check = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
        if not check.data:
            st.error("🚫 Sua entrada na arena foi revogada. Saindo...")
            time.sleep(2)
            st.session_state.jogador = None
            st.rerun()
            return
    # -------------------------------

    lista_antiga = jogo_atual['letras_tentadas']
    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()


def reiniciar_arena_completa():
    if "baloes_disparados" in st.session_state:
        del st.session_state.baloes_disparados
    supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
    supabase.table("forca_disputa_arena").update({
        "pergunta": "Aguardando nova pergunta...", "palavra": "ARENA",
        "letras_tentadas": "", "erros": 0, "restantes": 0, "ultimo_jogador": "SISTEMA"
    }).eq("id", 1).execute()
    st.rerun()

# ==================================================
# 4. INTERFACE DA ARENA (CHAMADA ÚNICA)
# ==================================================

@st.fragment(run_every=2)
def arena_viva():
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Mestre Pratti iniciar...")
        return

    # RESTAURADO: Proporção original 3 por 1
    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        # RESTAURADO: Proporção original 1 por 2
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo.get('erros', 0)
        ultimo_player = jogo.get('ultimo_jogador', "SISTEMA")
        
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

            # --- LÓGICA DE PONTUAÇÃO (Original) ---
            if vitoria and erros_atuais < 6:
                id_palavra_atual = f"vitoria_{palavra_alvo}_{contagem}"
                if id_palavra_atual not in st.session_state:
                    if st.session_state.jogador == ultimo_player:
                        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
                        pts = res_p.data['pontos'] if res_p.data else 0
                        supabase.table("forca_disputa_ranking").update({"pontos": pts + 10}).eq("jogador", st.session_state.jogador).execute()
                        st.toast(f"🏆 +10 pontos por vencer o desafio!")
                    st.session_state[id_palavra_atual] = True

            # --- MENSAGENS DE INTERFACE (Original) ---
            if vitoria and contagem == 0:
                st.subheader("🏆 ARENA CONQUISTADA!")
                st.success(f"🌟 **{ultimo_player}** venceu o desafio final!")
            elif erros_atuais >= 6 and contagem == 0:
                st.subheader("💀 FIM DA LINHA")
                st.error("A arena caiu no último desafio!")
            else:
                prefixo = f"📝 Pergunta {contagem}" if contagem > 0 else "🔥 PERGUNTA FINAL"
                st.subheader(prefixo)
                st.info(f"❓ **DICA:** {jogo['pergunta']}")

            # --- LÓGICA DE EXIBIÇÃO CORRIGIDA ---
            # Usamos o caractere Unicode \u2003 (Em Space) que é um espaço largo 
            # Ele não é "ignorado" pelo navegador dentro das crases.
            espaco_largo = "\u2003\u2003" 
            
            texto_visual = "".join([
                espaco_largo if l == " " else 
                f"{l} " if (l in tentadas or erros_atuais >= 6) else 
                "_ " 
                for l in palavra_alvo
            ])
            
            st.markdown(f"## `{texto_visual}`")
            st.caption(f"Última jogada por: **{ultimo_player}**")

        # --- CONTROLE DO TECLADO E SEGURANÇA (Original) ---
        if not vitoria and erros_atuais < 6:
            if st.session_state.jogador != "PRATTI":
                valido = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
                if not valido.data:
                    st.warning("⚠️ Sua entrada na arena foi revogada pelo Mestre.")
                    if st.button("SAIR DA ARENA", key="btn_sair_arena_expulso"):
                        st.session_state.jogador = None
                        st.rerun()
                    st.stop()

            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                if cols_tec[i % 9].button(letra, key=f"arena_teclado_{letra}", disabled=ja_foi, use_container_width=True):
                    registrar_jogada(letra, jogo)
                    st.rerun()
        elif not (contagem == 0) and vitoria:
             st.info("✅ Palavra correta! Aguardando o Mestre lançar a próxima.")

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).execute()
        jogadores_faciais = [r for r in res_rank.data if r['jogador'] != "PRATTI"]
        for i, r in enumerate(jogadores_faciais[:10]):
            st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")


            
# EXECUÇÃO DA ARENA
arena_viva()


# ==================================================
# 5. PAINEL DO ADMIN (PRATTI) - CONTROLES CENTRALIZADOS
# ==================================================
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE", expanded=True):
        if "fila_perguntas" not in st.session_state:
            st.session_state.fila_perguntas = []

        col_adm1, col_adm2, col_adm3 = st.columns([2, 1, 1])
        
        with col_adm1:
            st.markdown("#### 📝 Carregar e Lançar")
            arquivo = st.file_uploader("Arquivo .docx", type=["docx"], key="mestre_upload")
            
            if st.button("📥 PROCESSAR ARQUIVO"):
                if arquivo:
                    st.session_state.fila_perguntas = extrair_dados_do_docx(arquivo)
                    st.success(f"{len(st.session_state.fila_perguntas)} questões carregadas!")
                else:
                    st.error("Selecione um arquivo primeiro.")

            if st.button("🚀 LANÇAR PRÓXIMA PERGUNTA", use_container_width=True):
                if st.session_state.fila_perguntas:
                    total_antes = len(st.session_state.fila_perguntas)
                    proxima = st.session_state.fila_perguntas.pop(0)
                    valor_banco = total_antes if len(st.session_state.fila_perguntas) > 0 else 0

                    supabase.table("forca_disputa_arena").update({
                        "pergunta": proxima['pergunta'], "palavra": proxima['resposta'],
                        "letras_tentadas": "", "erros": 0, "restantes": valor_banco,
                        "ultimo_jogador": "SISTEMA"
                    }).eq("id", 1).execute()
                    st.rerun()
                else:
                    st.warning("A fila de perguntas está vazia!")
        
        with col_adm2:
            st.markdown("#### 🔄 Arena")
            st.metric("Na Fila", len(st.session_state.fila_perguntas))
            st.write("")
            # BOTÃO REINICIAR (Apenas aqui agora)
            if st.button("🔄 REINICIAR ARENA", use_container_width=True):
                reiniciar_arena_completa()

        with col_adm3:
            st.markdown("#### 👥 Jogadores")
            # BOTÃO EXCLUIR TODOS
            if st.button("🗑️ LIMPAR TUDO", use_container_width=True, type="primary", help="Exclui todos os jogadores do ranking"):
                supabase.table("forca_disputa_ranking").delete().neq("jogador", "PRATTI").execute()
                st.rerun()
            
            st.divider()
            # LISTA PARA EXCLUSÃO INDIVIDUAL
            res_jogadores = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "PRATTI").execute()
            for j in res_jogadores.data:
                c1, c2 = st.columns([3, 1])
                c1.caption(j['jogador'])
                if c2.button("❌", key=f"excluir_{j['jogador']}"):
                    supabase.table("forca_disputa_ranking").delete().eq("jogador", j['jogador']).execute()
                    st.rerun()
