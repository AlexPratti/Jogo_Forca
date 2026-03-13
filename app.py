import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Jogo da Forca Python", layout="wide")

# CSS para replicar o design das imagens (Dark Mode + Detalhes)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: white; }
    .display-box { 
        background-color: #444444; padding: 40px; border: 2px solid #777; 
        text-align: center; font-size: 22px; min-height: 180px;
        display: flex; align-items: center; justify-content: center; border-radius: 5px;
    }
    .letra-box { 
        background-color: white; color: black; font-size: 28px; 
        font-weight: bold; width: 45px; text-align: center; 
        border-bottom: 4px solid red; margin: 4px; display: inline-block;
        border-radius: 3px;
    }
    .titulo-forca { color: #FF8C00; font-size: 35px; font-weight: bold; text-align: center; }
    .status-azul { background-color: #0099FF; color: white; text-align: center; padding: 5px; font-weight: bold; margin-bottom: 10px; }
    div.stButton > button { width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'game_active' not in st.session_state:
    st.session_state.update({
        'user_name': '', 'active': False, 'won': False, 'errors': 0,
        'guessed_letters': set(), 'score': 0,
        'word': "DISJUNTOR", # Exemplo
        'hint': "Dispositivo de proteção elétrica que desliga o circuito em caso de sobrecarga."
    })

# --- FUNÇÕES ---
def calcular_mensagem():
    nome = st.session_state.user_name.upper()
    pontos = st.session_state.score
    if pontos >= 70:
        return f"PARABÉNS! {nome}. VOCÊ FOI INCRÍVEL. SUA PONTUAÇÃO FOI DE {pontos} PONTOS."
    elif 50 <= pontos < 70:
        return f"{nome}. SUA PONTUAÇÃO FOI DE {pontos} PONTOS, MAS VOCÊ PODE MELHORAR."
    else:
        return f"{nome}. SUA PONTUAÇÃO FOI DE {pontos} PONTOS, ESTUDE MAIS."

# --- INTERFACE ---
if not st.session_state.user_name:
    st.session_state.user_name = st.text_input("DIGITE SEU NOME PARA JOGAR:")
    if st.session_state.user_name: st.rerun()
    st.stop()

# Botões Superiores
cols_top = st.columns(6)
with cols_top[0]: 
    if st.button("JOGAR"): st.session_state.active = True
with cols_top[1]: 
    if st.button("LIMPAR FORCA"): st.session_state.errors = 0
with cols_top[2]: 
    if st.button("RESETAR"): 
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

# Layout Principal
c_forca, c_jogo = st.columns([1, 3])

with c_forca:
    st.markdown("<div class='titulo-forca'>JOGO<br>DA<br>FORCA</div>", unsafe_allow_html=True)
    # Placeholder para a imagem da forca (você pode subir suas imagens pro GitHub e usar o link aqui)
    st.image("https://via.placeholder.com", width=200)

with c_jogo:
    # Caixa Central de Texto
    msg_final = calcular_mensagem() if st.session_state.won else st.session_state.hint
    st.markdown(f"<div class='display-box'>{msg_final}</div>", unsafe_allow_html=True)
    
    # Exibição da Palavra
    st.write("")
    word_display = "".join([f"<span class='letra-box'>{l if l in st.session_state.guessed_letters else '&nbsp;'}</span>" for l in st.session_state.word if l != " "])
    st.markdown(f"<div style='text-align: center;'>{word_display}</div>", unsafe_allow_html=True)

    # Teclado Virtual
    st.markdown("<div class='status-azul'>ESCOLHER UMA LETRA ABAIXO</div>", unsafe_allow_html=True)
    teclado = ["AÁÂÃEÉÊIÍOÓÔÕUÚ-", "BCÇDFGHJKLMNPQRSTVWXYZ"]
    
    for linha in teclado:
        cols = st.columns(len(linha))
        for i, letra in enumerate(linha):
            ja_foi = letra in st.session_state.guessed_letters
            if cols[i].button(letra, key=f"key_{letra}", disabled=ja_foi):
                st.session_state.guessed_letters.add(letra)
                if letra in st.session_state.word:
                    # Lógica simples de pontos: Proporcional ao acerto
                    st.session_state.score += int(100 / len(st.session_state.word))
                else:
                    st.session_state.errors += 1
                
                # Checa vitória
                if all(l in st.session_state.guessed_letters for l in st.session_state.word if l != " "):
                    st.session_state.won = True
                    st.session_state.score = 100 # Garante 100 no acerto total
                st.rerun()

# Rodapé de Sugestão
st.write("---")
c_sug1, c_sug2 = st.columns([1, 2])
with c_sug1: st.button("SUGERIR A PALAVRA")
with c_sug2: st.text_input("Sugerir", label_visibility="collapsed", key="input_sug")
