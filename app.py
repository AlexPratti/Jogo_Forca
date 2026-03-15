import streamlit as st
import os
from docx import Document
from io import BytesIO
from supabase import create_client

# ================================
# SUPABASE
# ================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]

supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# ================================
# SESSION STATE
# ================================
if 'pares' not in st.session_state:
    st.session_state.pares = []

if 'indice' not in st.session_state:
    st.session_state.indice = None

if 'acertos' not in st.session_state:
    st.session_state.acertos = 0

if 'derrotas' not in st.session_state:
    st.session_state.derrotas = 0

if 'pergunta' not in st.session_state:
    st.session_state.pergunta = None

if 'palavra' not in st.session_state:
    st.session_state.palavra = None

if 'letras_corretas' not in st.session_state:
    st.session_state.letras_corretas = []

if 'letras_erradas' not in st.session_state:
    st.session_state.letras_erradas = []

if 'erros' not in st.session_state:
    st.session_state.erros = 0

if 'max_erros' not in st.session_state:
    st.session_state.max_erros = 6


# ================================
# FUNÇÕES
# ================================

def extrair_perguntas_respostas(docx_file):
    doc = Document(docx_file)

    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    pares = []

    for i in range(0, len(linhas), 2):
        if i + 1 < len(linhas):
            pergunta = linhas[i]
            resposta = linhas[i+1].upper()
            pares.append((pergunta, resposta))

    return pares


def salvar_no_supabase(arquivo):
    try:

        supabase.storage.from_("forca").upload(
            path="arquivo_compartilhado.docx",
            file=arquivo.getvalue(),
            file_options={"upsert": True}
        )

        st.success("Arquivo enviado para o Supabase!")

    except Exception as e:
        st.error(f"Erro ao enviar arquivo: {e}")


def carregar_do_supabase():

    try:

        response = supabase.storage.from_("forca").download(
            "arquivo_compartilhado.docx"
        )

        return BytesIO(response)

    except Exception:
        return None


def carregar_perguntas():

    if not st.session_state.pares:

        arquivo = carregar_do_supabase()

        if arquivo:
            st.session_state.pares = extrair_perguntas_respostas(arquivo)


def iniciar_nova_pergunta():

    if not st.session_state.pares:
        return

    if st.session_state.indice is None:
        st.session_state.indice = 0
    else:
        st.session_state.indice += 1

    if st.session_state.indice < len(st.session_state.pares):

        pergunta, resposta = st.session_state.pares[st.session_state.indice]

        st.session_state.pergunta = pergunta
        st.session_state.palavra = resposta

        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.erros = 0

    else:

        st.session_state.pergunta = None
        st.session_state.palavra = None

        st.success("Fim das perguntas!")


# ================================
# LOGIN
# ================================

if "jogador" not in st.session_state:

    nome = st.text_input("Digite seu nome")

    if st.button("Entrar no jogo") and nome.strip():

        st.session_state.jogador = nome.strip().upper()

        carregar_perguntas()

        st.rerun()

else:

    st.markdown("<h1 style='color:black;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # ================================
    # ADMIN
    # ================================

    if st.session_state.jogador.lower() == "pratti":

        arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])

        if arquivo:

            salvar_no_supabase(arquivo)

            pares = extrair_perguntas_respostas(arquivo)

            st.session_state.pares = pares

    # ================================
    # CARREGAR PERGUNTAS
    # ================================

    carregar_perguntas()

    if not st.session_state.pares:

        st.warning("Nenhuma pergunta encontrada.")

        st.stop()

    # ================================
    # PLACAR
    # ================================

    st.markdown(
        f"""
        <div style='background-color:#222; color:white; padding:10px; border-radius:5px;'>
        Jogador: {st.session_state.jogador}<br>
        Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}<br>
        Erros atuais: {st.session_state.erros}/{st.session_state.max_erros}
        </div>
        """,
        unsafe_allow_html=True
    )

    col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

    # ================================
    # IMAGEM
    # ================================

    with col_forca:

        nome_imagem = f"erro{st.session_state.erros}.png"

        if os.path.exists(nome_imagem):
            st.image(nome_imagem)

    # ================================
    # CONTROLES
    # ================================

    with col_controles:

        label_btn = "JOGAR" if st.session_state.indice is None else "PRÓXIMO"

        if st.button(label_btn):

            iniciar_nova_pergunta()

            st.rerun()

        if st.button("RESETAR"):

            st.session_state.clear()

            st.rerun()

    # ================================
    # JOGO
    # ================================

    with col_jogo:

        if st.session_state.pergunta:

            st.subheader(st.session_state.pergunta)

            exibicao = " ".join(
                letra if letra in st.session_state.letras_corretas else "_"
                for letra in st.session_state.palavra
            )

            st.markdown(f"## {exibicao}")

            letras = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

            cols = st.columns(9)

            for i, l in enumerate(letras):

                disabled = l in st.session_state.letras_corretas or l in st.session_state.letras_erradas

                if cols[i % 9].button(l, key=l, disabled=disabled):

                    if l in st.session_state.palavra:

                        st.session_state.letras_corretas.append(l)

                    else:

                        st.session_state.letras_erradas.append(l)

                        st.session_state.erros += 1

                    st.rerun()

            # derrota
            if st.session_state.erros >= st.session_state.max_erros:

                st.error("💀 Você perdeu!")

                st.write(f"A palavra era: {st.session_state.palavra}")

                st.session_state.derrotas += 1

            # vitória
            elif all(l in st.session_state.letras_corretas for l in st.session_state.palavra):

                st.success("🎉 Você venceu!")

                st.session_state.acertos += 1

        else:

            st.info("Clique em JOGAR para começar.")
