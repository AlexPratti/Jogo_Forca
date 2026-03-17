import streamlit as st
import unicodedata
import random
from io import BytesIO
from docx import Document
from supabase import create_client
import time

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Arena da Forca", page_icon="⚔️", layout="wide")

# Funções de Apoio
def remover_acentos(texto):
    if not texto: return ""
    return "".join([c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        linhas =
        lista = []
        for i in range(0, len(linhas), 2):
            if i+1 < len(linhas):
                lista.append({"pergunta": linhas[i], "resposta": remover_acentos(linhas[i+1].upper())})
        return lista
    except: return []

# ==================================================
# 2. LOGIN E IDENTIFICAÇÃO
# ==================================================
if "jogador" not in st.session_state:
    st.title("⚔️ Bem-vindo à Arena da Forca")
    nome = st.text_input("Qual seu nome de competidor?").strip().upper()
    if st.button("Entrar na Disputa") and nome:
        st.session_state.jogador = nome
        # Registra no ranking se for novo
        supabase.table("forca_disputa_ranking").upsert({"jogador": nome}, on_conflict="jogador").execute()
        st.rerun()
    st.stop()

# ==================================================
# 3. INTERFACE E LÓGICA DA ARENA
# ==================================================
st.title(f"🎮 ARENA: {st.session_state.jogador}")

col_jogo, col_rank = st.columns([3, 1])

# --- LÓGICA DE SINCRONIZAÇÃO (FRAGMENTO) ---
@st.fragment(run_every=2)
def carregar_arena():
    # Busca estado global do jogo no Supabase
    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    
    letras_tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
    palavra_limpa = jogo['palavra'].replace(" ", "")
    venceu = all(l in letras_tentadas for l in palavra_limpa)
    perdeu = jogo['erros'] >= 6

    with col_jogo:
        st.subheader(f"❓ {jogo['pergunta']}")
        
        # Exibição da Palavra
        texto_exibicao = ""
        for letra in jogo['palavra']:
            if letra == " ": texto_exibicao += "  "
            elif letra in letras_tentadas or perdeu: texto_exibicao += f"{letra} "
            else: texto_exibicao += "_ "
        st.markdown(f"## `{texto_exibicao}`")

        # Status e Imagem da Forca
        st.write(f"💀 Erros da Equipe: **{jogo['erros']}/6** | Último chute: **{jogo['ultimo_jogador'] or 'Ninguém'}**")
        
        if venceu:
            st.success(f"🎉 PALAVRA DESCOBERTA! Vitória de todos!")
        elif perdeu:
            st.error(f"💀 FORCA! A palavra era {jogo['palavra']}")
        else:
            # Teclado Multiplayer
            alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols = st.columns(9)
            for i, letra in enumerate(alfabeto):
                btn_desabilitado = letra in letras_tentadas
                if cols[i % 9].button(letra, key=f"btn_{letra}", disabled=btn_desabilitado):
                    processar_chute(letra, jogo, letras_tentadas)

def processar_chute(letra, jogo_atual, letras_tentadas):
    novas_letras = jogo_atual['letras_tentadas'] + f",{letra}"
    novos_erros = jogo_atual['erros']
    
    # Se errou, aumenta o contador global de erros
    if letra not in jogo_atual['palavra']:
        novos_erros += 1
    
    # Atualiza o Supabase para que TODOS vejam a mudança
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador
    }).eq("id", 1).execute()

    # Se a letra estava na palavra, o jogador ganha 1 ponto no ranking
    if letra in jogo_atual['palavra']:
        supabase.rpc('increment_score', {'row_id': st.session_state.jogador}).execute() 
        # Nota: Se não quiser criar função RPC, use um select + update simples aqui.
        res_rank = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        novo_ponto = res_rank.data['pontos'] + 1
        supabase.table("forca_disputa_ranking").update({"pontos": novo_ponto}).eq("jogador", st.session_state.jogador).execute()

    st.rerun()

# --- RANKING LATERAL ---
with col_rank:
    st.markdown("### 🏆 Top Ranking")
    res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).limit(10).execute()
    for item in res_rank.data:
        st.write(f"{item['jogador']}: {item['pontos']} pts")

# --- PAINEL DO ADMIN (PRATTI) ---
if st.session_state.jogador == "PRATTI":
    with st.expander("⚙️ COMANDOS DO MESTRE"):
        arquivo = st.file_uploader("Novo arquivo de questões", type=["docx"])
        if st.button("🚀 LANÇAR NOVA PALAVRA") and arquivo:
            questoes = extrair_dados_do_docx(arquivo)
            if questoes:
                q = random.choice(questoes)
                supabase.table("forca_disputa_arena").update({
                    "pergunta": q['pergunta'],
                    "palavra": q['resposta'],
                    "letras_tentadas": "",
                    "erros": 0,
                    "ultimo_jogador": "Início"
                }).eq("id", 1).execute()
                st.success("Nova rodada iniciada!")
                time.sleep(1)
                st.rerun()
        
        if st.button("🧹 Resetar Ranking"):
            supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
            st.rerun()

# Inicia a execução do fragmento
carregar_arena()
