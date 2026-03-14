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
    if st.button("JOGAR"):
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
        st.rerun()
    st.button("CORES LETRAS")
    if st.button("SAIR DO JOGO"):
        del st.session_state["jogador"]
        st.rerun()
    if st.button("PRÓXIMO"):
        iniciar_nova_pergunta()
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

        # Teclado e lógica de jogo...
        # Condições de vitória ou derrota
        if st.session_state.erros >= st.session_state.max_erros:
            st.error("💀 Você foi enforcado! Game Over!")
            st.error(f"A resposta era: {st.session_state.palavra}")
            st.session_state.derrotas += 1
            st.snow()  # animação de derrota
        elif all(letra in st.session_state.letras_corretas for letra in st.session_state.palavra):
            st.balloons()
            st.success("Parabéns! Você acertou a resposta!")
            st.session_state.acertos += 1

        # Informações da rodada (não o placar geral)
        st.write(f"Letras erradas: {', '.join(st.session_state.letras_erradas)}")
        st.write(f"Tentativas restantes: {st.session_state.max_erros - st.session_state.erros}")
    else:
        st.info("Clique em **JOGAR** para começar.")
