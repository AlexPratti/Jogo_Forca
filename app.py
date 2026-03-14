import streamlit as st
import random
import string
from docx import Document

st.set_page_config(page_title="Jogo da Forca", page_icon="🎮")

# Upload do arquivo Word
arquivo = st.file_uploader("Carregue um arquivo Word (.docx)", type=["docx"])

# Função para extrair perguntas e respostas
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

# Se o usuário carregou um arquivo, usa perguntas/respostas dele
if arquivo:
    pares = extrair_perguntas_respostas(arquivo)
else:
    # fallback caso nenhum arquivo seja carregado
    pares = [
        ("Linguagem usada para ciência de dados?", "PYTHON"),
        ("Plataforma para hospedar repositórios?", "GITHUB"),
        ("Framework para apps interativos em Python?", "STREAMLIT")
    ]

# Inicialização do estado do jogo
if 'pares' not in st.session_state:
    st.session_state.pares = pares
    st.session_state.indice = None  # índice da pergunta atual
    st.session_state.acertos = 0
    st.session_state.derrotas = 0

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
        st.session_state.max_erros = 6
    else:
        st.session_state.pergunta = None
        st.session_state.palavra = None

st.title("🎮 Jogo da Forca")

# Placar
st.sidebar.title("📊 Placar")
st.sidebar.write(f"✅ Acertos: {st.session_state.acertos}")
st.sidebar.write(f"❌ Derrotas: {st.session_state.derrotas}")

# Botão para iniciar ou sortear nova pergunta
if st.button("Jogar / Sortear nova pergunta"):
    iniciar_nova_pergunta()
    st.rerun()

# Só mostra o jogo se houver pergunta ativa
if st.session_state.get("pergunta"):
    # Exibição da imagem baseada no número de erros
    nome_imagem = f"erro{st.session_state.erros}.png"
    try:
        st.image(nome_imagem, caption=f"Tentativas gastas: {st.session_state.erros}")
    except:
        st.warning(f"Imagem {nome_imagem} não encontrada.")

    # Exibição da pergunta (caixa cinza grande)
    st.markdown(
        f"<div style='background-color:#ddd; padding:15px; border-radius:5px; font-size:18px;'>"
        f"{st.session_state.pergunta}</div>",
        unsafe_allow_html=True
    )

    # Exibição da palavra com espaços
    exibicao = " ".join([letra if letra in st.session_state.letras_corretas else "_" for letra in st.session_state.palavra])
    st.subheader(exibicao)

    # Entrada do usuário
    chute = st.text_input("Digite uma letra:", max_chars=1).upper()

    if st.button("Verificar"):
        if chute and chute in string.ascii_uppercase:
            if chute in st.session_state.palavra:
                if chute not in st.session_state.letras_corretas:
                    st.session_state.letras_corretas.append(chute)
                    st.success(f"Acertou a letra {chute}!")
                else:
                    st.info(f"Você já tentou a letra {chute}.")
            else:
                if chute not in st.session_state.letras_erradas:
                    st.session_state.letras_erradas.append(chute)
                    st.session_state.erros += 1
                    st.error(f"A letra {chute} não está na palavra.")
                else:
                    st.info(f"Você já tentou a letra {chute}.")
        else:
            st.warning("Digite apenas uma letra válida (A-Z).")

    # Condições de vitória ou derrota
    if st.session_state.erros >= st.session_state.max_erros:
        st.error(f"Game Over! A resposta era: {st.session_state.palavra}")
        st.session_state.derrotas += 1
    elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra):
        st.balloons()
        st.success("Parabéns! Você acertou a resposta!")
        st.session_state.acertos += 1

    # Mostra as letras que já foram tentadas
    st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
    st.write(f"Tentativas restantes: {st.session_state.max_erros - st.session_state.erros}")

else:
    st.info("Clique em **Jogar / Sortear nova pergunta** para começar.")
