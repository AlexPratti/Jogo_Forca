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

# Entrada do nome do jogador
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.experimental_rerun()
else:
    # Interface principal
    st.markdown("<h1 style='color:orange;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # Linha de botões
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("JOGAR"):
            # lógica para iniciar nova pergunta
            pass
    with col2: st.button("LIMPAR FORCA")
    with col3: st.button("RESETAR")
    with col4: st.button("CORES LETRAS")
    with col5: st.button("SAIR DO JOGO")

    # Status do jogador
    st.write(f"Jogador: {st.session_state.jogador}")
    st.write(f"ERROS: {st.session_state.get('erros',0)}")

    # Mostrar imagem da forca conforme erros
    erros = st.session_state.get("erros",0)
    nome_imagem = f"erro{erros}.png"
    try:
        st.image(nome_imagem, caption=f"Erros: {erros}/6")
    except:
        st.warning(f"Imagem {nome_imagem} não encontrada.")

    # Caixa cinza com pergunta
    if st.session_state.get("pergunta"):
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
                    # lógica de verificação da letra
                    pass
    else:
        st.info("Clique em **JOGAR** para começar.")
