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
# Verifique se as chaves estão no secrets do Streamlit
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
        # Extrai linhas ignorando vazias
        linhas =
        
        lista_final = []
        for i in range(0, len(linhas), 2):
            if i+1 < len(linhas):
                pergunta = linhas[i]
                # A resposta é salva sem acentos e em maiúsculo para facilitar a comparação
                resposta = remover_acentos(linhas[i+1].upper())
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        st.error(f"Erro ao processar o Word: {e}")
        return []

# ==================================================
# 2. TELA DE LOGIN (INDIVIDUAL)
# ==================================================
if "jogador" not in st.session_state:
    st.title("⚔️ Bem-vindo à Arena da Forca")
    nome_digitado = st.text_input("Qual seu nome de competidor?").strip().upper()
    if st.button("Entrar na Disputa") and nome_digitado:
        st.session_state.jogador = nome_digitado
        # Garante que o jogador exista na tabela de ranking
        supabase.table("forca_disputa_ranking").upsert({"jogador": nome_digitado}, on_conflict="jogador").execute()
        st.rerun()
    st.stop()

# ==================================================
# 3. INTERFACE PRINCIPAL
# ==================================================
st.markdown(f"### 🕹️ Competidor: `{st.session_state.jogador}`")

col_jogo, col_rank = st.columns([3, 1])

# --- LÓGICA DE ATUALIZAÇÃO DO BANCO ---
def processar_chute(letra, jogo_atual, letras_tentadas_str):
    # Prepara a nova lista de letras tentadas
    novas_letras = f"{letras_tentadas_str},{letra}" if letras_tentadas_str else letra
    novos_erros = jogo_atual['erros']
    
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # Atualiza o estado global no Supabase
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

    # Se acertou a letra, ganha ponto no ranking
    if letra in jogo_atual['palavra']:
        res = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        pontos_atuais = res.data['pontos'] if res.data else 0
        supabase.table("forca_disputa_ranking").update({"pontos": pontos_atuais + 1}).eq("jogador", st.session_state.jogador).execute()

# --- ARENA EM TEMPO REAL (FRAGMENTO) ---
@st.fragment(run_every=2)
def arena_multiplayer():
    # 1. Busca os dados da partida global
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    
    if not jogo:
        st.warning("Jogo não inicializado no banco de dados.")
        return

    # Processa as letras já usadas
    letras_usadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
    palavra_limpa = jogo['palavra'].replace(" ", "")
    venceu = all(l in letras_usadas for l in palavra_limpa)
    perdeu = jogo['erros'] >= 6

    with col_jogo:
        st.info(f"❓ **PERGUNTA:** {jogo['pergunta']}")
        
        # Exibição da Palavra na Tela
        texto_visual = ""
        for letra in jogo['palavra']:
            if letra == " ": texto_visual += "  "
            elif letra in letras_usadas or perdeu: texto_visual += f"{letra} "
            else: texto_visual += "_ "
        st.markdown(f"## `{texto_visual}`")

        st.write(f"💀 Erros da Sala: **{jogo['erros']}/6** | Última ação: **{jogo['ultimo_jogador'] or 'Ninguém'}**")

        if venceu:
            st.success(f"🎉 PALAVRA DESCOBERTA! Vitória da sala!")
            st.balloons()
        elif perdeu:
            st.error(f"💀 FORCA! A palavra correta era: {jogo['palavra']}")
        else:
            # Teclado Virtual compartilhado
            alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            teclas = st.columns(9)
            for i, letra in enumerate(alfabeto):
                # Se a letra já foi usada por qualquer pessoa, o botão fica desativado
                ja_foi = letra in letras_usadas
                if teclas[i % 9].button(letra, key=f"key_{letra}", disabled=ja_foi, use_container_width=True):
                    processar_chute(letra, jogo, jogo['letras_tentadas'])
                    st.rerun()

    # --- RANKING ATUALIZADO ---
    with col_rank:
        st.markdown("### 🏆 Ranking")
        rank_res = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
        for i, r in enumerate(rank_res.data):
            st.write(f"{i+1}º {r['jogador']}: **{r['pontos']}**")

# Executa a arena
arena_multiplayer()

# --- PAINEL DO ADMINISTRADOR (EXCLUSIVO PRATTI) ---
if st.session_state.jogador == "PRATTI":
    st.divider()
    with st.expander("⚙️ PAINEL DO MESTRE (Comandos Pratti)"):
        st.write("Suba o arquivo Word e escolha uma palavra para todos os jogadores.")
        arquivo = st.file_uploader("Arquivo .docx", type=["docx"])
        
        if st.button("🚀 LANÇAR NOVA PALAVRA DO ARQUIVO"):
            if arquivo:
                lista = extrair_dados_do_docx(arquivo)
                if lista:
                    escolhida = random.choice(lista)
                    supabase.table("forca_disputa_arena").update({
                        "pergunta": escolhida['pergunta'],
                        "palavra": escolhida['resposta'],
                        "letras_tentadas": "",
                        "erros": 0,
                        "ultimo_jogador": "Mestre Pratti"
                    }).eq("id", 1).execute()
                    st.success("Nova palavra enviada para todos!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Selecione um arquivo primeiro.")
                
        if st.button("🧹 ZERAR PONTUAÇÃO DE TODOS"):
            supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
            st.success("Ranking resetado!")
            st.rerun()
