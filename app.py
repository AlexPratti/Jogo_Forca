import streamlit as st
import unicodedata
import random
import time
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
# Verifique se estas chaves estão no seu secrets do Streamlit
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
        # LINHA CORRIGIDA ABAIXO:
        linhas =
        
        lista_final = []
        for i in range(0, len(linhas), 2):
            if i+1 < len(linhas):
                pergunta = linhas[i]
                resposta = remover_acentos(linhas[i+1].upper())
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        st.error(f"Erro ao processar o Word: {e}")
        return []

# ==================================================
# 2. TELA DE LOGIN
# ==================================================
if "jogador" not in st.session_state:
    st.title("⚔️ Bem-vindo à Arena da Forca")
    nome_digitado = st.text_input("Qual seu nome de competidor?").strip().upper()
    if st.button("Entrar na Disputa") and nome_digitado:
        st.session_state.jogador = nome_digitado
        # Garante que o jogador exista no ranking
        supabase.table("forca_disputa_ranking").upsert({"jogador": nome_digitado}, on_conflict="jogador").execute()
        st.rerun()
    st.stop()

# ==================================================
# 3. INTERFACE E LÓGICA DE DISPUTA
# ==================================================
st.markdown(f"### 🕹️ Competidor: `{st.session_state.jogador}`")

# Criamos as colunas principais
col_jogo, col_rank = st.columns([3, 1])

# Função para atualizar o banco quando alguém clica numa letra
def registrar_clique(letra, jogo_atual):
    letras_usadas_str = jogo_atual['letras_tentadas']
    novas_letras = f"{letras_usadas_str},{letra}" if letras_usadas_str else letra
    novos_erros = jogo_atual['erros']
    
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # 1. Atualiza a mesa de jogo global
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

    # 2. Se acertou a letra, ganha ponto individual
    if letra in jogo_atual['palavra']:
        res = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        pts = res.data['pontos'] if res.data else 0
        supabase.table("forca_disputa_ranking").update({"pontos": pts + 1}).eq("jogador", st.session_state.jogador).execute()

# --- ARENA EM TEMPO REAL (FRAGMENTO) ---
@st.fragment(run_every=2)
def arena_multiplayer():
    # Busca dados globais
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    
    if not jogo:
        st.warning("Aguardando inicialização do jogo...")
        return

    letras_usadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
    palavra_limpa = jogo['palavra'].replace(" ", "")
    venceu = all(l in letras_usadas for l in palavra_limpa)
    perdeu = jogo['erros'] >= 6

    with col_jogo:
        st.info(f"❓ **DICA:** {jogo['pergunta']}")
        
        # Exibição da Palavra
        texto_visual = ""
        for letra in jogo['palavra']:
            if letra == " ": texto_visual += "  "
            elif letra in letras_usadas or perdeu: texto_visual += f"{letra} "
            else: texto_visual += "_ "
        st.markdown(f"## `{texto_visual}`")

        st.write(f"💀 Erros Coletivos: **{jogo['erros']}/6** | Último a jogar: **{jogo['ultimo_jogador'] or 'Ninguém'}**")

        if venceu:
            st.success(f"🎉 VITÓRIA! A palavra era {jogo['palavra']}!")
            st.balloons()
        elif perdeu:
            st.error(f"💀 DERROTA! A palavra era {jogo['palavra']}")
        else:
            # Teclado
            alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            teclas = st.columns(9)
            for i, letra in enumerate(alfabeto):
                ja_foi = letra in letras_usadas
                if teclas[i % 9].button(letra, key=f"btn_{letra}", disabled=ja_foi, use_container_width=True):
                    registrar_clique(letra, jogo)
                    st.rerun()

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
        for i, r in enumerate(res_rank.data):
            st.write(f"{i+1}º {r['jogador']}: **{r['pontos']}**")

# Inicia a Arena
arena_multiplayer()

# ==================================================
# 4. PAINEL DO ADMIN (PRATTI)
# ==================================================
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ COMANDOS DO MESTRE (PRATTI)"):
        arquivo = st.file_uploader("Suba o arquivo de questões", type=["docx"])
        
        if st.button("🚀 LANÇAR NOVA PALAVRA") and arquivo:
            questoes = extrair_dados_do_docx(arquivo)
            if questoes:
                q = random.choice(questoes)
                supabase.table("forca_disputa_arena").update({
                    "pergunta": q['pergunta'],
                    "palavra": q['resposta'],
                    "letras_tentadas": "",
                    "erros": 0,
                    "ultimo_jogador": "Início da Rodada"
                }).eq("id", 1).execute()
                st.success("Nova palavra lançada para todos!")
                time.sleep(1)
                st.rerun()
        
        if st.button("🧹 ZERAR RANKING"):
            supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
            st.success("Pontuação zerada!")
            st.rerun()
