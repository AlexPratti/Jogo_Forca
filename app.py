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
        # Extrai o texto de cada parágrafo
        todas_as_linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        lista_final = []
        for i in range(0, len(todas_as_linhas), 2):
            if i + 1 < len(todas_as_linhas):
                lista_final.append({
                    "pergunta": todas_as_linhas[i], 
                    "resposta": remover_acentos(todas_as_linhas[i+1].upper())
                })
        return lista_final
    except Exception as e:
        st.error(f"Erro no Word: {e}")
        return []

def trocar_pergunta():
    if "lista_perguntas" in st.session_state and st.session_state.lista_perguntas:
        if "perguntas_usadas" not in st.session_state:
            st.session_state.perguntas_usadas = []

        perguntas_disponiveis = [
            p for p in st.session_state.lista_perguntas 
            if p["pergunta"] not in st.session_state.perguntas_usadas
        ]

        if not perguntas_disponiveis:
            # Todas já foram usadas → fim de jogo, mas sem balões ainda
            supabase.table("forca_disputa_arena").update({
                "pergunta": "", "palavra": "",
                "letras_tentadas": "", "erros": 0,
                "ultimo_jogador": "Fim do Jogo",
                "vitoria_final": False,
                "status": "fim"
            }).eq("id", 1).execute()
            st.warning("⚠️ Todas as perguntas já foram usadas. O jogo terminou!")
            return False

        nova = random.choice(perguntas_disponiveis)
        st.session_state.perguntas_usadas.append(nova["pergunta"])

        supabase.table("forca_disputa_arena").update({
            "pergunta": nova['pergunta'], 
            "palavra": nova['resposta'],
            "letras_tentadas": "", 
            "erros": 0, 
            "ultimo_jogador": f"Sorteio por {st.session_state.jogador}",
            "vitoria_final": False,
            "status": "rodando"
        }).eq("id", 1).execute()
        return True
    return False



# ==================================================
# 2. TELA DE LOGIN
# ==================================================
if "jogador" not in st.session_state:
    st.title("⚔️ Bem-vindo à Arena da Forca")
    nome_digitado = st.text_input("Qual seu nome de competidor?").strip().upper()
    if st.button("Entrar na Disputa") and nome_digitado:
        st.session_state.jogador = nome_digitado
        supabase.table("forca_disputa_ranking").upsert({"jogador": nome_digitado}, on_conflict="jogador").execute()
        st.rerun()
    st.stop()

# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def registrar_jogada(letra, jogo_atual):
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

    # Ranking: Admin (PRATTI) não ganha pontos
    if letra in jogo_atual['palavra'] and st.session_state.jogador != "PRATTI":
        res = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        pts = res.data['pontos'] if res.data else 0
        supabase.table("forca_disputa_ranking").update({"pontos": pts + 1}).eq("jogador", st.session_state.jogador).execute()

# ==================================================
# 4. INTERFACE DA ARENA (BOTÕES NO TOPO)
# ==================================================

# --- BARRA DE COMANDOS SUPERIOR ---
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
with c1:
    st.markdown(f"### 🕹️ Competidor: `{st.session_state.jogador}`")
with c2:
    if st.button("🎮 Próxima Pergunta", use_container_width=True):
        if not trocar_pergunta():
            st.warning("Mestre precisa carregar o arquivo .docx primeiro!")
with c3:
    if st.button("🔄 Resetar Arena", use_container_width=True):
        supabase.table("forca_disputa_arena").update({
            "pergunta": "", "palavra": "",
            "letras_tentadas": "", "erros": 0,
            "ultimo_jogador": "Reset Manual",
            "vitoria_final": False
        }).eq("id", 1).execute()
        st.rerun()

with c4:
    if st.button("🚪 Sair", use_container_width=True, type="primary"):
        del st.session_state.jogador
        st.rerun()

st.divider()

@st.fragment(run_every=2)
def arena_viva():
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Mestre Pratti iniciar...")
        return

    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo['erros']
        
        with c_img:
            nome_img = f"erro{erros_atuais}.png"
            if os.path.exists(nome_img):
                st.image(nome_img, width=180)
            else:
                st.metric("Erros da Equipe", f"{erros_atuais}/6")

        with c_txt:
            st.info(f"❓ **DICA:** {jogo['pergunta']}")
            tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
            palavra_alvo = jogo['palavra']
            
            vitoria_rodada = True
            texto_visual = ""
            for letra in palavra_alvo:
                if letra == " ": texto_visual += "  "
                elif letra in tentadas or erros_atuais >= 6: texto_visual += letra + " "
                else:
                    texto_visual += "_ "
                    vitoria_rodada = False
            
            st.markdown(f"## `{texto_visual}`")
            st.caption(f"Última jogada por: **{jogo['ultimo_jogador']}**")

        # --- LÓGICA DE FIM DE JOGO ---
        total_perguntas = len(st.session_state.lista_perguntas) if "lista_perguntas" in st.session_state else 0
        usadas = len(st.session_state.perguntas_usadas) if "perguntas_usadas" in st.session_state else 0
        ultima_pergunta = (usadas == total_perguntas)

        if vitoria_rodada and erros_atuais < 6 and jogo['pergunta']:
            st.success("✅ Palavra Descoberta!")
            supabase.table("forca_disputa_arena").update({"vitoria_final": True}).eq("id", 1).execute()

            # Só solta balões se for a última pergunta
            if ultima_pergunta:
                vencedor = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(1).execute()
                if vencedor.data:
                    st.success(f"🏆 JOGO ENCERRADO! Vencedor: {vencedor.data[0]['jogador']} com {vencedor.data[0]['pontos']} pontos!")
                    st.balloons()

        elif erros_atuais >= 6 and jogo['pergunta']:
            st.error(f"💀 DERROTA! A resposta era: {palavra_alvo}")
            supabase.table("forca_disputa_arena").update({"vitoria_final": True}).eq("id", 1).execute()

            # Só solta balões se for a última pergunta
            if ultima_pergunta:
                vencedor = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(1).execute()
                if vencedor.data:
                    st.success(f"🏆 JOGO ENCERRADO! Vencedor: {vencedor.data[0]['jogador']} com {vencedor.data[0]['pontos']} pontos!")
                    st.balloons()

        else:
            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                if cols_tec[i % 9].button(letra, key=f"bt_{letra}", disabled=ja_foi, use_container_width=True):
                    registrar_jogada(letra, jogo)
                    st.rerun()

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
        for i, r in enumerate(res_rank.data):
            if r['jogador'] != "PRATTI":
                st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")



arena_viva()

# ==================================================
# 5. PAINEL DO ADMIN (PRATTI)
# ==================================================
with st.expander("🎩 Painel do Mestre (PRATTI)", expanded=True):
    # Upload do documento
    uploaded_file = st.file_uploader("📂 Carregar documento de perguntas", type=["csv", "xlsx", "txt"], key="upload_doc")
    if uploaded_file is not None:
        st.session_state.lista_perguntas = carregar_perguntas(uploaded_file)
        st.session_state.perguntas_usadas = []
        st.success(f"✅ Documento carregado com {len(st.session_state.lista_perguntas)} perguntas!")

    # Contador de progresso
    total_perguntas = len(st.session_state.lista_perguntas) if "lista_perguntas" in st.session_state else 0
    usadas = len(st.session_state.perguntas_usadas) if "perguntas_usadas" in st.session_state else 0

    if usadas < total_perguntas:
        st.info(f"📊 Progresso: Pergunta {usadas+1} de {total_perguntas}")
    else:
        st.info("📊 Todas as perguntas já foram usadas")

    # Botão próxima pergunta
    if st.button("➡️ Próxima Pergunta", key="btn_proxima", use_container_width=True):
        ok = trocar_pergunta()
        if not ok:
            st.warning("⚠️ Não há mais perguntas disponíveis. O jogo terminou!")
        st.rerun()

    # Botão reset
    if st.button("🔄 Resetar Arena", key="btn_reset", use_container_width=True):
        supabase.table("forca_disputa_arena").update({
            "pergunta": "", "palavra": "",
            "letras_tentadas": "", "erros": 0,
            "ultimo_jogador": "Reset Manual",
            "vitoria_final": False,
            "status": "aguardando"
        }).eq("id", 1).execute()
        st.session_state.perguntas_usadas = []
        st.rerun()

    # Botão remover todos jogadores
    if st.button("🔥 Remover TODOS os Jogadores e Resetar Jogo", key="btn_remover_todos", use_container_width=True):
        supabase.table("forca_disputa_ranking").delete().neq("jogador","").execute()
        supabase.table("forca_disputa_arena").update({
            "pergunta": "", "palavra": "",
            "letras_tentadas": "", "erros": 0,
            "ultimo_jogador": "Reset Geral",
            "vitoria_final": False,
            "status": "aguardando"
        }).eq("id", 1).execute()
        st.session_state.perguntas_usadas = []
        st.success("Todos os jogadores foram removidos e o jogo resetado!")
        st.rerun()
