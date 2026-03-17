import streamlit as st
import unicodedata
import random
import time
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO
# ==================================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Arena da Forca", page_icon="⚔️", layout="wide")

# --- FUNÇÕES DE APOIO ---
def remover_acentos(texto):
    if not texto: 
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        # Extração passo a passo para evitar erro de sintaxe
        todas_as_linhas = []
        for p in doc.paragraphs:
            texto_limpo = p.text.strip()
            if texto_limpo:
                todas_as_linhas.append(texto_limpo)
        
        lista_final = []
        # Pula de 2 em 2 para pegar Pergunta e Resposta
        for i in range(0, len(todas_as_linhas), 2):
            if i + 1 < len(todas_as_linhas):
                p = todas_as_linhas[i]
                r = remover_acentos(todas_as_linhas[i+1].upper())
                lista_final.append({"pergunta": p, "resposta": r})
        return lista_final
    except Exception as e:
        st.error(f"Erro no Word: {e}")
        return []

# ==================================================
# 2. TELA DE LOGIN
# ==================================================
if "jogador" not in st.session_state:
    st.title("⚔️ Bem-vindo à Arena da Forca")
    nome_digitado = st.text_input("Qual seu nome de competidor?").strip().upper()
    if st.button("Entrar na Disputa") and nome_digitado:
        st.session_state.jogador = nome_digitado
        # Salva o jogador no ranking do Supabase
        supabase.table("forca_disputa_ranking").upsert({"jogador": nome_digitado}, on_conflict="jogador").execute()
        st.rerun()
    st.stop()

# ==================================================
# 3. LÓGICA DE JOGO (GLOBAL)
# ==================================================
def registrar_jogada(letra, jogo_atual):
    lista_antiga = jogo_atual['letras_tentadas']
    if lista_antiga:
        novas_letras = lista_antiga + "," + letra
    else:
        novas_letras = letra
        
    novos_erros = jogo_atual['erros']
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # Atualiza a mesa de jogo para todos
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

    # Se acertou, ganha 1 ponto no ranking
    if letra in jogo_atual['palavra']:
        res = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        pts = res.data['pontos'] if res.data else 0
        supabase.table("forca_disputa_ranking").update({"pontos": pts + 1}).eq("jogador", st.session_state.jogador).execute()

# ==================================================
# 4. INTERFACE DA ARENA (ATUALIZAÇÃO AUTOMÁTICA)
# ==================================================
st.markdown(f"### 🕹️ Competidor Ativo: `{st.session_state.jogador}`")

# Fragmento que roda sozinho a cada 2 segundos para sincronizar as telas
@st.fragment(run_every=2)
def arena_viva():
    # Busca dados no Supabase
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    
    if not jogo:
        st.warning("O administrador ainda não iniciou a partida.")
        return

    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        st.info(f"❓ **DICA:** {jogo['pergunta']}")
        
        # Processa as letras usadas
        tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
        palavra_alvo = jogo['palavra']
        erros_atuais = jogo['erros']
        
        # Monta o texto visual
        vitoria = True
        texto_visual = ""
        for letra in palavra_alvo:
            if letra == " ":
                texto_visual += "  "
            elif letra in tentadas or erros_atuais >= 6:
                texto_visual += letra + " "
            else:
                texto_visual += "_ "
                vitoria = False
        
        st.markdown(f"## `{texto_visual}`")
        st.write(f"💀 Erros da Sala: **{erros_atuais}/6** | Última jogada: **{jogo['ultimo_jogador']}**")

        if vitoria and erros_atuais < 6:
            st.success("🎉 VITÓRIA COLETIVA!")
            st.balloons()
        elif erros_atuais >= 6:
            st.error(f"💀 DERROTA! A resposta era: {palavra_alvo}")
        else:
            # Teclado Virtual
            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_teclado = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                if cols_teclado[i % 9].button(letra, key=f"btn_{letra}", disabled=ja_foi):
                    registrar_jogada(letra, jogo)
                    st.rerun()

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
        if res_rank.data:
            for i, r in enumerate(res_rank.data):
                st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")

# Chama a função da arena
arena_viva()

# ==================================================
# 5. PAINEL DO ADMIN (PRATTI)
# ==================================================
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE (PRATTI)"):
        arquivo = st.file_uploader("Arquivo .docx com Perguntas e Respostas", type=["docx"])
        
        if st.button("🚀 LANÇAR NOVA PALAVRA") and arquivo:
            lista_q = extrair_dados_do_docx(arquivo)
            if lista_q:
                escolhida = random.choice(lista_q)
                supabase.table("forca_disputa_arena").update({
                    "pergunta": escolhida['pergunta'],
                    "palavra": escolhida['resposta'],
                    "letras_tentadas": "",
                    "erros": 0,
                    "ultimo_jogador": "Mestre Pratti"
                }).eq("id", 1).execute()
                st.success("Nova rodada iniciada!")
                time.sleep(1)
                st.rerun()
        
        if st.button("🧹 ZERAR PONTOS DO RANKING"):
            supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
            st.success("Ranking zerado!")
            st.rerun()
