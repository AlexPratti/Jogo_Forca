import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Jogo da Forca VBA-Python", layout="wide")

# --- ESTILIZAÇÃO CSS (DESIGN FIEL ÀS IMAGENS) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: white; }
    
    /* Botão ENTRAR NO JOGO e outros botões */
    div.stButton > button {
        background-color: #333333 !important;
        color: white !important;
        border: 1px solid #555555 !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 40px !important;
    }
    
    /* Caixa de Pergunta/Mensagem Final */
    .display-box { 
        background-color: #444444; padding: 30px; border: 2px solid #777; 
        text-align: center; font-size: 22px; min-height: 180px;
        display: flex; align-items: center; justify-content: center; border-radius: 5px;
    }

    /* Blocos das Letras (Brancos com linha vermelha) */
    .letra-box { 
        background-color: white; color: black; font-size: 28px; 
        font-weight: bold; width: 45px; text-align: center; 
        border-bottom: 4px solid red; margin: 4px; display: inline-block;
        border-radius: 3px;
    }

    .titulo-forca { color: #FF8C00; font-size: 40px; font-weight: bold; text-align: center; line-height: 1.1; }
    .status-azul { background-color: #0099FF; color: white; text-align: center; padding: 5px; font-weight: bold; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO DO JOGO ---
if 'logado' not in st.session_state:
    st.session_state.update({
        'logado': False, 'user_name': '', 'game_active': False,
        'guessed_letters': set(), 'errors': 0, 'won': False, 'score': 0,
        'word': "DISJUNTOR", # Palavra padrão
        'hint': "Pressione 'JOGAR' para sortear uma pergunta ou comece a chutar as letras."
    })

# --- FUNÇÕES DE LÓGICA ---
def reset_game():
    st.session_state.guessed_letters = set()
    st.session_state.errors = 0
    st.session_state.won = False
    st.session_state.score = 0
    st.session_state.game_active = True

def get_final_message():
    nome = st.session_state.user_name.upper()
    pontos = st.session_state.score
    if pontos >= 70:
        return f"PARABÉNS! {nome}. VOCÊ FOI INCRÍVEL. SUA PONTUAÇÃO FOI DE {pontos} PONTOS."
    elif 50 <= pontos < 70:
        return f"{nome}. SUA PONTUAÇÃO FOI DE {pontos} PONTOS, MAS VOCÊ PODE MELHORAR."
    else:
        return f"{nome}. SUA PONTUAÇÃO FOI DE {pontos} PONTOS, ESTUDE MAIS."

# --- TELA 1: LOGIN ---
if not st.session_state.logado:
    st.markdown("### DIGITE SEU NOME PARA JOGAR:")
    nome_input = st.text_input("", key="login_name", label_visibility="collapsed")
    
    if st.button("ENTRAR NO JOGO"):
        if len(nome_input.strip()) >= 2:
            st.session_state.user_name = nome_input
            st.session_state.logado = True
            st.rerun()
        else:
            st.warning("⚠️ O nome deve ter pelo menos 2 letras.")
    st.stop()

# --- TELA 2: O JOGO ---

# 1. Barra de Ferramentas Superior
cols_top = st.columns(6)
with cols_top[0]: 
    if st.button("JOGAR"): reset_game(); st.rerun()
with cols_top[1]: 
    if st.button("LIMPAR FORCA"): st.session_state.errors = 0; st.rerun()
with cols_top[2]: 
    if st.button("RESETAR"): st.session_state.logado = False; st.rerun()
with cols_top[3]: st.button("CORES LETRAS")
with cols_top[4]: 
    if st.button("SAIR DO JOGO"): st.session_state.logado = False; st.rerun()

st.write("---")

# 2. Área Central (Forca e Pergunta)
col_left, col_right = st.columns([1, 3])

with col_left:
    st.markdown("<div class='titulo-forca'>JOGO<br>DA<br>FORCA</div>", unsafe_allow_html=True)
    st.write(f"👤 Jogador: **{st.session_state.user_name.upper()}**")
    
    # Visual da Forca baseado em erros
    partes = ["CABEÇA", "BRAÇO DIREITO", "BRAÇO ESQUERDO", "PERNA DIREITA", "PERNA ESQUERDA"]
    if st.session_state.errors > 0:
        st.error(f"ERROS: {st.session_state.errors}")
        for i in range(st.session_state.errors):
            if i < len(partes): st.write(f"❌ {partes[i]}")
    else:
        st.info("Nenhum erro ainda!")

with col_right:
    # Caixa de Texto Principal (Dica ou Resultado)
    conteudo = get_final_message() if st.session_state.won else st.session_state.hint
    st.markdown(f"<div class='display-box'>{conteudo}</div>", unsafe_allow_html=True)
    
    # Exibição da Palavra (Campos brancos)
    st.write("")
    palavra_limpa = st.session_state.word.upper()
    display = ""
    acertos = 0
    for letra in palavra_limpa:
        if letra == " ":
            display += "&nbsp;&nbsp;"
        elif letra in st.session_state.guessed_letters:
            display += f"<span class='letra-box'>{letra}</span>"
            acertos += 1
        else:
            display += "<span class='letra-box'>&nbsp;</span>"
    
    st.markdown(f"<div style='text-align: center;'>{display}</div>", unsafe_allow_html=True)

    # Teclado de Letras
    st.markdown("<div class='status-azul'>ESCOLHER UMA LETRA ABAIXO</div>", unsafe_allow_html=True)
    
    alfabeto = ["AÁÂÃBCÇDEÉÊFGHIÍ", "JKLMNOÓÔÕPQRSTUVWXYZ-"]
    for linha in alfabeto:
        cols_key = st.columns(len(linha))
        for i, letra in enumerate(linha):
            ja_clicou = letra in st.session_state.guessed_letters
            # Se já clicou, o botão fica desabilitado (simulando a mudança de cor/estado)
            if cols_key[i].button(letra, key=f"btn_{letra}", disabled=ja_clicou):
                st.session_state.guessed_letters.add(letra)
                if letra not in palavra_limpa:
                    st.session_state.errors += 1
                
                # Cálculo de Pontos Proporcional (Máximo 100)
                letras_unicas = set(palavra_limpa.replace(" ", ""))
                acertos_atuais = len([l for l in letras_unicas if l in st.session_state.guessed_letters])
                st.session_state.score = int((acertos_atuais / len(letras_unicas)) * 100)

                # Verifica vitória
                if all(l in st.session_state.guessed_letters for l in palavra_limpa if l != " "):
                    st.session_state.won = True
                st.rerun()

# 3. Rodapé (Sugestão de Palavra)
st.write("---")
c_sug_btn, c_sug_input = st.columns([1, 2])
with c_sug_btn:
    if st.button("SUGERIR A PALAVRA"):
        sugestao = st.session_state.get('input_sug', '').upper()
        if sugestao == st.session_state.word:
            st.session_state.score = 100
            st.session_state.won = True
            st.rerun()
        else:
            st.error("Palavra Incorreta!")

with c_sug_input:
    st.text_input("Digite a resposta direta:", key="input_sug", label_visibility="collapsed")

st.markdown(f"### PONTUAÇÃO: {st.session_state.score} / 100")
