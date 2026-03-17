import streamlit as st
import random
from docx import Document
import unicodedata

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="centered")

# CSS para responsividade em celular
st.markdown("""
    <style>
    @media (max-width: 600px) {
        .stButton button {
            font-size: 18px !important;
            padding: 12px !important;
        }
        .stMarkdown {
            font-size: 16px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
def remover_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt)
                   if unicodedata.category(c) != 'Mn')

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        texto_bruto = "\n".join([p.text for p in doc.paragraphs])
        linhas = [linha.strip() for linha in texto_bruto.splitlines() if linha.strip()]

        lista_final = []
        for i in range(0, len(linhas), 2):
            if i+1 < len(linhas):
                pergunta = linhas[i]
                resposta = remover_acentos(linhas[i+1].upper())
                lista_final.append({"pergunta": pergunta, "resposta": resposta})

        random.shuffle(lista_final)
        return lista_final
    except Exception as e:
        st.error(f"Erro ao processar o Word: {e}")
        return []

# ---------------- ESTADO INICIAL ----------------
if "jogador" not in st.session_state:
    st.session_state.jogador = ""
if "pares" not in st.session_state:
    st.session_state.pares = []
if "indice" not in st.session_state:
    st.session_state.indice = -1
if "acertos" not in st.session_state:
    st.session_state.acertos = 0
if "derrotas" not in st.session_state:
    st.session_state.derrotas = 0
if "erros" not in st.session_state:
    st.session_state.erros = 0
if "max_erros" not in st.session_state:
    st.session_state.max_erros = 6
if "letras_corretas" not in st.session_state:
    st.session_state.letras_corretas = []
if "letras_erradas" not in st.session_state:
    st.session_state.letras_erradas = []
if "fim_do_jogo" not in st.session_state:
    st.session_state.fim_do_jogo = False

# ---------------- ENTRADA DE USUÁRIO ----------------
if not st.session_state.jogador:
    st.session_state.jogador = st.text_input("Digite seu nome:", "").strip()
    if st.session_state.jogador:
        st.success(f"Bem-vindo, {st.session_state.jogador}!")

uploaded_file = st.file_uploader("Upload de arquivo de perguntas (.docx)", type=["docx"])
if uploaded_file is not None and not st.session_state.pares:
    st.session_state.pares = extrair_dados_do_docx(uploaded_file)

# ---------------- CABEÇALHO ----------------
if st.session_state.jogador:
    st.subheader(f"JOGO DA FORCA - JOGADOR: {st.session_state.jogador}")
    st.write(f"✅ Acertos: {st.session_state.acertos}")
    st.write(f"❌ Derrotas: {st.session_state.derrotas}")
    st.write(f"⚠️ Erros: {st.session_state.erros} / {st.session_state.max_erros}")

    # ---------------- IMAGEM DA FORCA ----------------
    img_path = f"forca{st.session_state.erros}.png"
    try:
        st.image(img_path, use_container_width=True)
    except:
        st.warning("Imagem da forca não encontrada. Verifique os arquivos forca0.png até forca6.png.")

    # ---------------- PERGUNTA ----------------
    if st.session_state.indice >= 0 and st.session_state.indice < len(st.session_state.pares):
        st.subheader(st.session_state.pares[st.session_state.indice]["pergunta"])

    # ---------------- PALAVRA ATUAL ----------------
    if "palavra" in st.session_state and st.session_state.palavra:
        palavra_atual = "".join([letra if letra in st.session_state.letras_corretas else "_" 
                                 for letra in st.session_state.palavra])
        st.write("Palavra:", palavra_atual)

        # Verificação de vitória
        if "_" not in palavra_atual and not st.session_state.fim_do_jogo:
            st.success("Você acertou! 🎉")
            st.session_state.acertos += 1
            st.session_state.fim_do_jogo = True

        # Verificação de derrota
        if st.session_state.erros >= st.session_state.max_erros and not st.session_state.fim_do_jogo:
            st.error(f"Você perdeu! A palavra era: {st.session_state.palavra}")
            st.session_state.derrotas += 1
            st.session_state.fim_do_jogo = True

    # ---------------- BOTÕES DE CONTROLE ----------------
    if st.button("🚀 JOGAR", use_container_width=True):
        st.session_state.indice += 1
        if st.session_state.indice < len(st.session_state.pares):
            item_atual = st.session_state.pares[st.session_state.indice]
            st.session_state.pergunta = item_atual["pergunta"]
            st.session_state.palavra = item_atual["resposta"]
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.session_state.erros = 0
            st.session_state.fim_do_jogo = False
        else:
            st.success("🎉 Fim de Jogo!")
            st.session_state.fim_do_jogo = True
        st.rerun()

    if st.button("🔄 Resetar Jogo", use_container_width=True):
        jogador = st.session_state.jogador
        st.session_state.pares = []
        st.session_state.indice = -1
        st.session_state.acertos = 0
        st.session_state.derrotas = 0
        st.session_state.erros = 0
        st.session_state.max_erros = 6
        st.session_state.letras_corretas = []
        st.session_state.letras_erradas = []
        st.session_state.fim_do_jogo = False
        st.session_state.jogador = jogador
        st.rerun()

    if st.button("❌ Sair do Jogo", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ---------------- TECLADO VIRTUAL ----------------
    if "palavra" in st.session_state and st.session_state.palavra and not st.session_state.fim_do_jogo:
        alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        colunas_teclas = st.columns(4)  # menos colunas para celular

        for i, letra in enumerate(alfabeto):
            if colunas_teclas[i % 4].button(letra, use_container_width=True):
                if letra in st.session_state.palavra:
                    st.session_state.letras_corretas.append(letra)
                else:
                    st.session_state.letras_erradas.append(letra)
                    st.session_state.erros += 1
                st.rerun()
