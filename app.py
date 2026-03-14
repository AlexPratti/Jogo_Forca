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
    st.session_state.fim_de_jogo = False

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
        st.session_state.fim_de_jogo = False
    else:
        st.session_state.pergunta = None
        st.session_state.palavra = None
        st.session_state.fim_de_jogo = True
# === Fluxo de entrada do nome do jogador ===
if "jogador" not in st.session_state:
    nome = st.text_input("Digite seu nome:")
    if st.button("Entrar no jogo") and nome.strip():
        st.session_state.jogador = nome.strip().upper()
        st.rerun()
else:
    # === Interface principal ===
    st.markdown("<h1 style='color:orange;'>JOGO DA FORCA</h1>", unsafe_allow_html=True)

    # 🔝 Placar e status fixos no topo
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

    # Layout com três colunas: forca, controles, jogo
    col_forca, col_controles, col_jogo = st.columns([1,0.8,2])

    with col_forca:
        nome_imagem = f"erro{st.session_state.erros}.png"
        try:
            st.image(nome_imagem, caption="Forca")
        except:
            st.warning(f"Imagem {nome_imagem} não encontrada.")

    with col_controles:
        st.markdown("### Controles")

        # Botão dinâmico JOGAR/PRÓXIMO
        label_btn = "JOGAR" if st.session_state.indice is None else "PRÓXIMO"
        if st.button(label_btn):
            iniciar_nova_pergunta()
            st.rerun()

        if st.button("LIMPAR FORCA"):
            st.session_state.erros = 0
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.rerun()

        if st.button("RESETAR"):
            st.session_state.indice = 0
            pergunta, resposta = st.session_state.pares[0]
            st.session_state.pergunta = pergunta
            st.session_state.palavra = resposta
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.session_state.erros = 0
            st.session_state.acertos = 0
            st.session_state.derrotas = 0
            st.session_state.fim_de_jogo = False
            st.rerun()

        st.button("CORES LETRAS")

        if st.button("SAIR DO JOGO"):
            # Remove jogador
            del st.session_state["jogador"]
            # Resetar todo o estado
            st.session_state.indice = None
            st.session_state.acertos = 0
            st.session_state.derrotas = 0
            st.session_state.pergunta = None
            st.session_state.palavra = None
            st.session_state.letras_corretas = []
            st.session_state.letras_erradas = []
            st.session_state.erros = 0
            st.session_state.fim_de_jogo = False
            st.rerun()




    
    with col_jogo:
        if st.session_state.pergunta:
            st.markdown(
                f"<div style='background-color:#444; color:white; padding:15px; border-radius:5px; font-size:18px;'>"
                f"{st.session_state.pergunta}</div>",
                unsafe_allow_html=True
            )

            exibicao = " ".join([letra if letra in st.session_state.letras_corretas else "_" for letra in st.session_state.palavra])
            st.subheader(exibicao)

            letras = ["A","Á","Â","Ã","Ä","Å","B","C","Ç","D","E","É","Ê","Ë","F","G","H","I","Í","Î","Ï",
                      "J","K","L","M","N","Ñ","O","Ó","Ô","Õ","Ö","P","Q","R","S","T","U","Ú","Û","Ü","V","W","X","Y","Z"]

            st.markdown("<h3 style='background-color:blue; color:white; padding:5px;'>ESCOLHER UMA LETRA ABAIXO</h3>", unsafe_allow_html=True)

            jogo_ativo = (
                st.session_state.erros < st.session_state.max_erros and
                not all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra)
            )

            cols = st.columns(8, gap="small")
            for i, letra in enumerate(letras):
                with cols[i % 8]:
                    if st.button(letra, key=f"btn_{letra}"):
                        if not jogo_ativo:
                            st.warning("A rodada terminou! Clique em PRÓXIMO para continuar.")
                        else:
                            if letra in st.session_state.palavra:
                                if letra not in st.session_state.letras_corretas:
                                    st.session_state.letras_corretas.append(letra)
                                    st.success(f"Acertou a letra {letra}!")
                                    st.rerun()
                            else:
                                if letra not in st.session_state.letras_erradas:
                                    st.session_state.letras_erradas.append(letra)
                                    st.session_state.erros += 1
                                    st.error(f"A letra {letra} não está na palavra.")
                                    st.rerun()

            # Condições de vitória ou derrota
            if st.session_state.erros >= st.session_state.max_erros:
                st.error("💀 Você foi enforcado! Game Over!")
                st.error(f"A resposta era: {st.session_state.palavra}")
                st.session_state.derrotas += 1
                st.snow()
            elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra):
                st.balloons()
                st.success("Parabéns! Você acertou a resposta!")
                st.session_state.acertos += 1

            st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
            st.write(f"Tentativas restantes: {st.session_state.max_erros - st.session_state.erros}")
        else:
            if st.session_state.fim_de_jogo:
                st.markdown("<h2 style='color:red;'>🏁 FIM DE JOGO</h2>", unsafe_allow_html=True)
                st.write(f"Placar final → Acertos: {st.session_state.acertos} | Derrotas: {st.session_state.derrotas}")
            else:
                st.info("Clique em **JOGAR** para começar.")
