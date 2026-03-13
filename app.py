import streamlit as st
import random

# Configuração da página
st.set_page_config(page_title="Jogo da Forca", page_icon="🎮")

# Lista de palavras para o jogo
palavras = ["PYTHON", "GITHUB", "CODIGO", "PROGRAMACAO", "STREAMLIT"]

# Inicialização do estado do jogo
if 'palavra' not in st.session_state:
    st.session_state.palavra = random.choice(palavras)
    st.session_state.letras_corretas = []
    st.session_state.letras_erradas = []
    st.session_state.erros = 0

st.title("🎮 Jogo da Forca")

# Exibição da imagem baseada no número de erros
# Se erros > 0, ele tenta carregar erro1.png, erro2.png, etc.
if st.session_state.erros > 0:
    nome_imagem = f"erro{st.session_state.erros}.png"
    try:
        st.image(nome_imagem, caption=f"Tentativas gastas: {st.session_state.erros}")
    except:
        st.warning(f"Imagem {nome_imagem} não encontrada no repositório.")

# Lógica para mostrar a palavra (ex: P _ T _ O N)
exibicao = "".join([letra if letra in st.session_state.letras_corretas else " _ " for letra in st.session_state.palavra])
st.subheader(exibicao)

# Entrada do usuário
chute = st.text_input("Digite uma letra:", max_chars=1).upper()

if st.button("Verificar"):
    if chute:
        if chute in st.session_state.palavra:
            if chute not in st.session_state.letras_corretas:
                st.session_state.letras_corretas.append(chute)
                st.success("Acertou!")
        else:
            if chute not in st.session_state.letras_erradas:
                st.session_state.letras_erradas.append(chute)
                st.session_state.erros += 1
                st.error("Errou!")

# Condições de vitória ou derrota
if st.session_state.erros >= 5:
    st.error(f"Game Over! A palavra era: {st.session_state.palavra}")
    if st.button("Reiniciar Jogo"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra):
    st.balloons()
    st.success("Parabéns! Você venceu!")
    if st.button("Jogar Novamente"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Mostra as letras que já foram tentadas
st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
