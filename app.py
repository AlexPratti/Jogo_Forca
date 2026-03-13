import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Forca VBA para Python", layout="wide")

# CSS para manter o design Dark e os blocos de letras brancos
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: white; }
    .display-box { 
        background-color: #444444; padding: 30px; border: 2px solid #777; 
        text-align: center; font-size: 20px; min-height: 150px; border-radius: 5px;
    }
    .letra-box { 
        background-color: white; color: black; font-size: 25px; 
        font-weight: bold; width: 40px; text-align: center; 
        border-bottom: 4px solid red; margin: 3px; display: inline-block;
    }
    .status-azul { background-color: #0099FF; color: white; text-align: center; padding: 5px; font-weight: bold; }
    div.stButton > button { width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'guessed_letters' not in st.session_state:
    st.session_state.guessed_letters = set()

# --- TELA INICIAL (LOGIN) ---
if not st.session_state.logado:
    st.write("DIGITE SEU NOME PARA JOGAR:")
    nome_temp = st.text_input("", key="input_nome", label_visibility="collapsed")
    
    # BOTÃO SOLICITADO
    if st.button("ENTRAR NO JOGO"):
        if nome_temp:
            st.session_state.user_name = nome_temp
            st.session_state.logado = True
            st.rerun() # Atualiza para mostrar a interface do jogo
        else:
            st.error("Por favor, insira seu nome antes de entrar.")
    st.stop() # Trava a execução aqui até que o botão seja clicado

# --- INTERFACE DO JOGO (SÓ APARECE APÓS CLICAR EM ENTRAR) ---

# Botões Superiores
cols_top = st.columns(6)
with cols_top[0]: st.button("JOGAR")
with cols_top[1]: st.button("LIMPAR FORCA")
with cols_top[2]: 
    if st.button("RESETAR"):
        st.session_state.logado = False
        st.session_state.guessed_letters = set()
        st.rerun()
with cols_top[5]: st.button("SAIR DO JOGO")

st.write("---")

# Corpo do Jogo
c_esq, c_dir = st.columns([1, 2])

with c_esq:
    st.markdown("<h1 style='color:#FF8C00; text-align:center;'>JOGO<br>DA<br>FORCA</h1>", unsafe_allow_html=True)
    st.write(f"👤 Jogador: **{st.session_state.user_name.upper()}**")
    # Espaço para a imagem da forca
    st.image("https://via.placeholder.com", width=200)

with c_dir:
    # Caixa de Dica/Mensagem
    st.markdown("<div class='display-box'>Pressione 'JOGAR' para iniciar ou selecione uma letra abaixo.</div>", unsafe_allow_html=True)
    
    # Exibição da Palavra Exemplo (BENJAMIN)
    palavra = "BENJAMIN"
    word_html = "".join([f"<span class='letra-box'>{l if l in st.session_state.guessed_letters else '&nbsp;'}</span>" for l in palavra])
    st.markdown(f"<div style='text-align: center; margin-top: 20px;'>{word_html}</div>", unsafe_allow_html=True)

    # Teclado Virtual
    st.write("")
    st.markdown("<div class='status-azul'>ESCOLHER UMA LETRA ABAIXO</div>", unsafe_allow_html=True)
    
    alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    teclado_cols = st.columns(13)
    for i, letra in enumerate(alfabeto):
        with teclado_cols[i % 13]:
            if st.button(letra, key=f"k_{letra}"):
                st.session_state.guessed_letters.add(letra)
                st.rerun()

# Rodapé de Sugestão
st.write("---")
col_sug1, col_sug2 = st.columns([1, 3])
with col_sug1: st.button("SUGERIR A PALAVRA")
with col_sug2: st.text_input("Sugerir", label_visibility="collapsed", key="sug_final")
