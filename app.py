import streamlit as st
import random
from docx import Document

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮", layout="wide")

# CSS para fundo escuro e título laranja
st.markdown(
    """
    <style>
    body { background-color: #111; color: white; }
    .stButton>button {
        background-color: #333; color: white; border-radius: 5px; padding: 8px 16px;
    }
    .stButton>button:hover { background-color: #555; color: orange; }
    </style>
    """,
    unsafe_allow_html=True
)

# Upload do arquivo Word
arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])

def extrair_perguntas_respostas(docx_file):
    doc = Document(docx_file)
    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    pares = []
    for i in range(0, len(linhas), 2):
        if i+1 < len(linhas):
            pergunta = linhas[i]
            resposta = linhas[i+1].upper()
            pares.append((pergunta, resposta))
    return pares

# Carregar perguntas
if arquivo:
    pares = extrair_perguntas_respostas(arquivo)
else:
    pares = [
        ("Linguagem usada para ciência de dados?", "PYTHON"),
        ("Plataforma para hospedar repositórios?", "GITHUB"),
        ("Framework para apps interativos em Python?", "STREAMLIT")
    ]

# Inicialização do estado
if 'pares' not in st.session_state:
    st.session_state.pares = pares
    st.session_state.indice = None
    st.session_state.acertos = 0
    st.session_state.derrotas = 0
    st.session_state.pergunta = None
    st.session_state.palavra = None
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0
    st.session_state.max_erros = 6

def iniciar_nova_pergunta():
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

# === Fluxo de entrada do nome do jogador ===
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    # === Interface principal ===
    st.markdown("<h1 style='color:orange;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # Linha de botões
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("JOGAR"):
            iniciar_nova_pergunta()
            st.rerun()
    with col2: st.button("LIMPAR FORCA")
    with col3: st.button("RESETAR")
    with col4: st.button("CORES LETRAS")
    with col5: st.button("SAIR DO JOGO")

    # Status do jogador
    st.write(f"Jogador: {st.session_state.jogador}")
    st.write(f"ERROS: {st.session_state.erros}")

    # Mostrar imagem da forca conforme erros (erro0 até erro6)
    nome_imagem = f"erro{st.session_state.erros}.png"
    try:
        st.image(nome_imagem, caption=f"Erros: {st.session_state.erros}/{st.session_state.max_erros}")
    except:
        st.warning(f"Imagem {nome_imagem} não encontrada.")

    # Caixa cinza com pergunta
    if st.session_state.pergunta:
        st.markdown(
            f"<div style='background-color:#444; color:white; padding:15px; border-radius:5px; font-size:18px;'>"
            f"{st.session_state.pergunta}</div>",
            unsafe_allow_html=True
        )

        # Palavra com espaços
        exibicao = " ".join([letra if letra in st.session_state.letras_corretas else "_" for letra in st.session_state.palavra])
        st.subheader(exibicao)

        # Teclado de letras
        letras = ["A","Á","Â","Ã","Ä","Å","B","C","Ç","D","E","É","Ê","Ë","F","G","H","I","Í","Î","Ï",
                  "J","K","L","M","N","Ñ","O","Ó","Ô","Õ","Ö","P","Q","R","S","T","U","Ú","Û","Ü","V","W","X","Y","Z"]

        st.markdown("<h3 style='background-color:blue; color:white; padding:5px;'>ESCOLHER UMA LETRA ABAIXO</h3>", unsafe_allow_html=True)
        cols = st.columns(10)
        for i, letra in enumerate(letras):
            with cols[i % 10]:
                if st.button(letra, key=f"btn_{letra}"):
                    if letra in st.session_state.palavra:
                        if letra not in st.session_state.letras_corretas:
                            st.session_state.letras_corretas.append(letra)
                            st.success(f"Acertou a letra {letra}!")
                    else:
                        if letra not in st.session_state.letras_erradas:
                            st.session_state.letras_erradas.append(letra)
                            st.session_state.erros += 1
                            st.error(f"A letra {letra} não está na palavra.")

        # Condições de vitória ou derrota
        if st.session_state.erros >= st.session_state.max_erros:
            st.error("💀 Você foi enforcado! Game Over!")
            st.error(f"A resposta era: {st.session_state.palavra}")
            st.session_state.derrotas += 1
        elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra):
            st.balloons()
            st.success("Parabéns! Você acertou a resposta!")
            st.session_state.acertos += 1

        # Letras erradas
        st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
        st.write(f"Tentativas restantes: {st.session_state.max_erros - st.session_state.erros}")

    else:
        st.info("Clique em **JOGAR** para começar.")
