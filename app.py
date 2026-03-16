import streamlit as st
import os
from docx import Document
from io import BytesIO
from supabase import create_client
import random
import unicodedata

# ================================
# Configuração Supabase
# ================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# ================================
# Funções Auxiliares
# ================================
def remover_acentos(texto):
    """Remove acentos e cedilha para facilitar o jogo"""
    return "".join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')

def extrair_perguntas_respostas(docx_file):
    try:
        doc = Document(docx_file)
        # O segredo: Ignora as linhas vazias que aparecem no seu Word
        linhas =
        
        pares = []
        # Pega de 2 em 2: Linha de texto 1 (Pergunta), Próxima linha de texto (Resposta)
        for i in range(0, len(linhas) - 1, 2):
            pergunta = linhas[i]
            # Limpa a resposta (Maiúsculas e sem acentos)
            resposta = remover_acentos(linhas[i+1].upper().strip())
            pares.append((pergunta, resposta))
        
        random.shuffle(pares)
        return pares
    except Exception as e:
        st.error(f"Erro ao ler o Word: {e}")
        return []

def salvar_no_supabase(arquivo):
    try:
        # Upload com upsert=True para sobrescrever o arquivo antigo
        supabase.storage.from_("forca").upload(
            path="arquivo_compartilhado.docx",
            file=arquivo.getvalue(),
            upsert=True
        )
        # Limpa o estado para forçar o recarregamento total
        st.session_state.pares = []
        st.session_state.indice = -1
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.session_state.novo_arquivo_carregado = True
        st.success("Arquivo enviado com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro no Supabase: {e}")

def carregar_do_supabase():
    try:
        response = supabase.storage.from_("forca").download("arquivo_compartilhado.docx")
        return BytesIO(response)
    except:
        return None

# ================================
# Inicialização do estado
# ================================
if 'pares' not in st.session_state:
    st.session_state.pares = []
    st.session_state.indice = -1
    st.session_state.acertos = 0
    st.session_state.derrotas = 0
    st.session_state.pergunta = None
    st.session_state.palavra = None
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0
    st.session_state.max_erros = 6
    st.session_state.fim_de_jogo = False
    st.session_state.novo_arquivo_carregado = False

# ================================
# Lógica de Carregamento
# ================================
def carregar_perguntas():
    if st.session_state.novo_arquivo_carregado or not st.session_state.pares:
        arquivo_bruto = carregar_do_supabase()
        if arquivo_bruto:
            novos_pares = extrair_perguntas_respostas(arquivo_bruto)
            if novos_pares:
                st.session_state.pares = novos_pares
                st.session_state.novo_arquivo_carregado = False

def iniciar_nova_pergunta():
    carregar_perguntas()
    if not st.session_state.pares:
        st.warning("Nenhuma pergunta disponível.")
        return
    
    st.session_state.indice += 1
    if st.session_state.indice < len(st.session_state.pares):
        pergunta, resposta = st.session_state.pares[st.session_state.indice]
        st.session_state.pergunta = pergunta
        st.session_state.palavra = resposta
        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.erros = 0
        st.session_state.fim_de_jogo = False
    else:
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.info("Fim do jogo!")

# ================================
# Interface
# ================================
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    st.markdown("<h1 style='color:black;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # Painel do Admin
    if st.session_state.jogador.lower() == "pratti":
        with st.expander("⚙️ Admin - Upload de Perguntas"):
            arq = st.file_uploader("Arquivo .docx", type=["docx"])
            if st.button("Atualizar Banco de Perguntas"):
                if arq:
                    salvar_no_supabase(arq)
                else:
                    st.warning("Selecione um arquivo.")

    carregar_perguntas()

    if not st.session_state.pares:
        st.warning("Aguardando perguntas do administrador...")
    else:
        # Placar
        st.info(f"Jogador: {st.session_state.jogador} | Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}")

        col1, col2, col3 = st.columns([1,1,2])

        with col1:
            img = f"erro{st.session_state.erros}.png"
            if os.path.exists(img): st.image(img)

        with col2:
            if st.button("JOGAR / PRÓXIMO", use_container_width=True):
                iniciar_nova_pergunta()
                st.rerun()
            if st.button("RESETAR TUDO", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        with col3:
            if st.session_state.pergunta:
                st.subheader(f"Dica: {st.session_state.pergunta}")
                
                # Exibição da palavra
                display = " ".join(l if l in st.session_state.letras_corretas or l == " " else "_" for l in st.session_state.palavra)
                st.markdown(f"## `{display}`")

                # Teclado
                letras = "ABCÇDEFGHIJKLMNOPQRSTUVWXYZ"
                perdeu = st.session_state.erros >= st.session_state.max_erros
                venceu = all(l in st.session_state.letras_corretas or l == " " for l in st.session_state.palavra)

                btn_cols = st.columns(7)
                for i, l in enumerate(letras):
                    ja_foi = l in st.session_state.letras_corretas or l in st.session_state.letras_erradas
                    if btn_cols[i%7].button(l, key=f"k_{l}", disabled=ja_foi or perdeu or venceu):
                        if l in st.session_state.palavra:
                            st.session_state.letras_corretas.append(l)
                        else:
                            st.session_state.letras_erradas.append(l)
                            st.session_state.erros += 1
                        st.rerun()

                if perdeu:
                    st.error(f"Você perdeu! Era: {st.session_state.palavra}")
                    if not st.session_state.fim_de_jogo:
                        st.session_state.derrotas += 1
                        st.session_state.fim_de_jogo = True
                elif venceu:
                    st.success("Parabéns! Você acertou!")
                    if not st.session_state.fim_de_jogo:
                        st.session_state.acertos += 1
                        st.session_state.fim_de_jogo = True
            else:
                st.write("Clique em JOGAR para começar.")
