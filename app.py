import streamlit as st
import unicodedata
import random
import time
import os
import string
import urllib.parse
from io import BytesIO
from docx import Document
from supabase import create_client

# ==================================================
# 1. CONEXÃO E CONFIGURAÇÃO
# ==================================================
URL_SUPABASE = st.secrets["URL_SUPABASE"]
KEY_SUPABASE = st.secrets["KEY_SUPABASE"]
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

st.set_page_config(page_title="Arena da Forca", page_icon="⚔️", layout="wide")

# --- FUNÇÕES DE APOIO ---
def remover_acentos(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def extrair_dados_do_docx(arquivo_docx):
    try:
        doc = Document(arquivo_docx)
        texto_bruto = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt: texto_bruto.append(txt)
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    txt = celula.text.strip()
                    if txt and txt not in texto_bruto: texto_bruto.append(txt)
        lista_final = []
        for i in range(0, len(texto_bruto), 2):
            if i + 1 < len(texto_bruto):
                pergunta = texto_bruto[i]
                resposta = remover_acentos(texto_bruto[i+1].upper().replace(" ", ""))
                lista_final.append({"pergunta": pergunta, "resposta": resposta})
        return lista_final
    except Exception as e:
        st.error(f"Erro ao ler o documento Word: {e}")
        return []

def gerar_senha_aleatoria():
    # Gera uma senha alfanumérica estável de 4 dígitos em maiúsculo (Ex: K9F2)
    caracteres = string.ascii_uppercase + string.digits
    return "".join(random.choice(caracteres) for _ in range(4))

# ==================================================
# 2. LOGIN E ESTADO (PRESERVAÇÃO E SEGURANÇA)
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

# Trava local ultra rápida contra cliques múltiplos indesejados
if "clique_bloqueado" not in st.session_state:
    st.session_state.clique_bloqueado = False

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    
    # Busca a senha contendo o prefixo forca_ no banco de dados
    try:
        res_arena = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
        senha_valida = res_arena.data.get('forca_senha_acesso', '1234') if res_arena.data else '1234'
    except Exception:
        senha_valida = '1234'

    nome = st.text_input("Digite seu nome para entrar na Arena:", key="input_nome")
    nome_upper = nome.strip().upper() if nome else ""
    
    # Exibe o campo de senha apenas para os jogadores comuns
    if nome_upper and nome_upper != "TREINAMENTOWLI":
        senha_digitada = st.text_input("Digite a Senha da Arena (Fornecida pelo Mestre):", type="password", key="input_senha")
    else:
        senha_digitada = None

    if st.button("ENTRAR NA ARENA"):
        if nome:
            if nome_upper == "TREINAMENTOWLI":
                st.session_state.jogador = nome_upper
                # Mestre gera e atualiza a coluna forca_senha_acesso
                nova_senha = gerar_senha_aleatoria()
                try:
                    supabase.table("forca_disputa_arena").update({"forca_senha_acesso": nova_senha}).eq("id", 1).execute()
                except Exception:
                    pass
                st.rerun()
            else:
                # Jogador comum valida contra a coluna forca_senha_acesso
                if senha_digitada and senha_digitada.strip().upper() == senha_valida.upper():
                    st.session_state.jogador = nome_upper
                    check_user = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", nome_upper).execute()
                    
                    if check_user.data:
                        st.toast(f"👋 Bem-vindo de volta, {nome_upper}! Seus pontos foram mantidos.")
                    else:
                        supabase.table("forca_disputa_ranking").upsert(
                            {"jogador": nome_upper, "pontos": 0}, 
                            on_conflict="jogador"
                        ).execute()
                    st.rerun()
                else:
                    st.error("🔑 Senha incorreta ou inválida para esta rodada. Peça o acesso ao Mestre.")
        else:
            st.warning("Por favor, digite um nome.")
    st.stop()
# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def calcular_proximo_turno(jogador_atual):
    """Calcula quem é estritamente o próximo jogador na ordem alfabética."""
    try:
        # Busca todos os jogadores participantes ordenados alfabeticamente
        res = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "TREINAMENTOWLI").order("jogador").execute()
        lista_jogadores = [r['jogador'] for r in res.data]
        
        if not lista_jogadores:
            return ""
        if len(lista_jogadores) == 1:
            return lista_jogadores[0]
            
        # Encontra o índice do jogador que acabou de jogar e avança de forma circular
        if jogador_atual in lista_jogadores:
            idx = lista_jogadores.index(jogador_atual)
            idx_proximo = (idx + 1) % len(lista_jogadores)
            return lista_jogadores[idx_proximo]
        else:
            return lista_jogadores[0]
    except Exception:
        return ""

def registrar_jogada(letra, jogo_atual):
    # Proteção para o Admin: Garante que o Admin não seja expulso ou processado como jogador
    if st.session_state.jogador == "TREINAMENTOWLI":
        return

    # Proteção de segurança otimizada para os jogadores normais contra quedas de rede
    try:
        check = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
        if not check.data:
            st.session_state.jogador = None
            st.rerun()
            return
    except Exception:
        pass

    # Ativa a trava local instantânea no milissegundo do clique
    st.session_state.clique_bloqueado = True

    # Variáveis de controle extraídas do banco
    lista_antiga = jogo_atual['letras_tentadas']
    tentadas = [l.strip() for l in lista_antiga.split(",") if l.strip()]
    
    # Se a letra já foi tentada por outra pessoa, cancela a operação
    if letra in tentadas:
        st.session_state.clique_bloqueado = False
        return

    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    palavra_alvo = jogo_atual['palavra']
    
    # Lógica de Pontuação por Letra (Mantida idêntica à original)
    if letra in palavra_alvo:
        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        if res_p.data:
            pts_atuais = res_p.data['pontos']
            supabase.table("forca_disputa_ranking").update({"pontos": pts_atuais + 5}).eq("jogador", st.session_state.jogador).execute()
            st.toast(f"🎯 Boa! +5 pontos pela letra {letra}!")
    else:
        novos_erros += 1
    
    # Define quem será o único jogador autorizado na próxima rodada
    proximo = calcular_proximo_turno(st.session_state.jogador)
    
    # Atualiza a Arena no Supabase com os novos prefixos forca_
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador,
        "forca_proximo_turno": proximo
    }).eq("id", 1).execute()


def reiniciar_arena_completa():
    if "baloes_disparados" in st.session_state:
        del st.session_state.baloes_disparados
    supabase.table("forca_disputa_ranking").update({"pontos": 0}).neq("jogador", "").execute()
    
    # Recupera as configurações e senhas atuais para não perdê-las no reset
    modo_atual = "LIVRE"
    senha_atual = "1234"
    try:
        res = supabase.table("forca_disputa_arena").select("forca_modo_jogo", "forca_senha_acesso").eq("id", 1).single().execute()
        if res.data:
            modo_atual = res.data.get('forca_modo_jogo', 'LIVRE')
            senha_atual = res.data.get('forca_senha_acesso', '1234')
    except Exception:
        pass

    supabase.table("forca_disputa_arena").update({
        "pergunta": "Aguardando nova pergunta...", "palavra": "ARENA",
        "letras_tentadas": "", "erros": 0, "restantes": 0, "ultimo_jogador": "SISTEMA",
        "forca_modo_jogo": modo_atual, "forca_senha_acesso": senha_atual, "forca_proximo_turno": ""
    }).eq("id", 1).execute()
    st.session_state.clique_bloqueado = False
    st.rerun()
# ==================================================
# 4. INTERFACE DA ARENA
# ==================================================

@st.fragment(run_every=2)
def arena_viva():
    # Garante o reset da trava local a cada nova renderização do fragmento
    st.session_state.clique_bloqueado = False

    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Administrador do Jogo iniciar...")
        return

    # TOCA MÚSICA SE O JOGO ESTIVER ATIVO (Mantido idêntico)
    if jogo['pergunta'] != "Aguardando nova pergunta..." and jogo['erros'] < 6:
        if os.path.exists("musica.mp3"):
            st.audio("musica.mp3", format="audio/mp3", loop=True, autoplay=True)

    # CORREÇÃO: Restaurada a proporção exata [3, 1] do seu código original
    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        # CORREÇÃO: Restaurada a proporção exata [1, 2] do seu código original
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo.get('erros', 0)
        ultimo_player = jogo.get('ultimo_jogador', "SISTEMA")
        modo_jogo = jogo.get('forca_modo_jogo', "LIVRE")
        proximo_autorizado = jogo.get('forca_proximo_turno', "")
        
        with c_img:
            nome_img = f"erro{erros_atuais}.png"
            if os.path.exists(nome_img):
                st.image(nome_img, width=180)
            else:
                st.metric("Erros da Equipe", f"{erros_atuais}/6")

        with c_txt:
            contagem = jogo.get('restantes', 0)
            tentadas = [l.strip() for l in jogo['letras_tentadas'].split(",") if l.strip()]
            palavra_alvo = jogo['palavra']
            vitoria = all((letra == " " or letra in tentadas) for letra in palavra_alvo)

            # --- LÓGICA DE PONTUAÇÃO POR PALAVRA ---
            if vitoria and erros_atuais < 6:
                id_palavra_atual = f"vitoria_{palavra_alvo}_{contagem}"
                if id_palavra_atual not in st.session_state:
                    if st.session_state.jogador == ultimo_player and st.session_state.jogador != "TREINAMENTOWLI":
                        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
                        pts = res_p.data['pontos'] if res_p.data else 0
                        supabase.table("forca_disputa_ranking").update({"pontos": pts + 10}).eq("jogador", st.session_state.jogador).execute()
                        st.toast(f"🏆 +10 pontos por vencer o desafio!")
                    st.session_state[id_palavra_atual] = True
                    
            # --- MENSAGENS DE INTERFACE E EMPATE ---
            if (vitoria or erros_atuais >= 6) and contagem == 0:
                rank_final = supabase.table("forca_disputa_ranking").select("*").neq("jogador", "TREINAMENTOWLI").order("pontos", desc=True).execute().data
                if rank_final:
                    max_pts = rank_final[0]['pontos']
                    vencedores = [r['jogador'] for r in rank_final if r['pontos'] == max_pts]
                    nomes = " & ".join(vencedores)
                    st.markdown(f"<h2 style='font-size: 30px;'>🏁 FIM DE JOGO! Vencedor(es): <b>{nomes}</b> com {max_pts} pts</h2>", unsafe_allow_html=True)
                st.error("💀 A ARENA FOI ENCERRADA.")
            else:
                prefixo = f"📝 Pergunta {contagem}" if contagem > 0 else "🔥 PERGUNTA FINAL"
                st.markdown(f"<h3 style='font-size: 24px; margin-bottom: 0px;'>{prefixo}</h3>", unsafe_allow_html=True)
                
                pergunta_texto = jogo['pergunta']
                st.markdown(
                    f"""
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 20px;">
                        <span style="font-size: 22px; color: #004085;">
                            ❓ <b>VALE 5 pts (letra) / 10 pts (vitória):</b> {pergunta_texto}
                        </span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    
            # Palavra oculta (Mantida original)
            texto_visual = "".join([f"{l} " if (l == " " or l in tentadas or erros_atuais >= 6) else "_ " for l in palavra_alvo])
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center;">
                    <code style="font-size: 20px; color: #ff4b4b; font-weight: bold;">{texto_visual}</code>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.caption(f"Última jogada por: **{ultimo_player}** | Formato: **{modo_jogo}**")

        # --- LÓGICA DE VALIDAÇÃO DE TURNOS EXCLUSIVOS ---
        autorizado_a_jogar = True
        mensagem_turno = ""
        
        if modo_jogo == "TURNOS" and not vitoria and erros_atuais < 6:
            if not proximo_autorizado or proximo_autorizado == "":
                mensagem_turno = "🔥 **Arena aberta!** Qualquer jogador pode dar o primeiro palpite."
                autorizado_a_jogar = True
            else:
                if st.session_state.jogador == proximo_autorizado:
                    mensagem_turno = f"⚔️ **SUA VEZ, {st.session_state.jogador}!** Faça a sua jogada agora."
                    autorizado_a_jogar = True
                else:
                    mensagem_turno = f"⏳ **AGUARDE!** É a vez do jogador: **{proximo_autorizado}**."
                    autorizado_a_jogar = False

        if mensagem_turno:
            st.info(mensagem_turno)

        # --- CONTROLE DO TECLADO ---
        if not vitoria and erros_atuais < 6:
            if st.session_state.jogador != "TREINAMENTOWLI":
                try:
                    valido = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
                    if not valido.data:
                        st.warning("⚠️ Sua entrada na arena foi revogada pelo Mestre.")
                        if st.button("SAIR", key="btn_sair_arena"):
                            st.session_state.jogador = None
                            st.rerun()
                        st.stop()
                except Exception:
                    pass

            letras_abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
            cols_tec = st.columns(9)
            for i, letra in enumerate(letras_abc):
                ja_foi = letra in tentadas
                
                # Trava rígida: desativa se a letra já foi, se o clique local foi acionado ou se não for o turno dele
                botao_desabilitado = ja_foi or (not autorizado_a_jogar) or st.session_state.clique_bloqueado
                
                if cols_tec[i % 9].button(letra, key=f"arena_tec_{letra}", disabled=botao_desabilitado, use_container_width=True):
                    st.session_state.clique_bloqueado = True
                    registrar_jogada(letra, jogo)
                    st.rerun()
        elif not (contagem == 0) and vitoria:
             st.info("✅ Palavra correta! Aguardando o Administrador...")

    with col_rank:
        st.markdown("### 🏆 Ranking")
        res_rank = supabase.table("forca_disputa_ranking").select("*").order("pontos", desc=True).execute()
        jogadores_faciais = [r for r in res_rank.data if r['jogador'] != "TREINAMENTOWLI"]
        for i, r in enumerate(jogadores_faciais[:10]):
            st.write(f"{i+1}º {r['jogador']}: {r['pontos']} pts")

arena_viva()

# ==================================================
# 5. PAINEL DO ADMIN (TREINAMENTOWLI)
# ==================================================
if st.session_state.jogador == "TREINAMENTOWLI":
    st.divider()
    
    # Criando as duas abas exclusivas solicitadas para o Mestre
    aba_jogo, aba_acesso = st.tabs(["🎮 JOGO & LANÇAMENTOS", "🔑 CONTROLE DE ACESSO & QR CODE"])
    
    # --------------------------------------------------
    # ABA 1: GERENCIAMENTO DE PERGUNTAS E ARENA
    # --------------------------------------------------
    with aba_jogo:
        with st.expander("⚙️ CONTROLE DA ARENA", expanded=True):
            if "fila_perguntas" not in st.session_state:
                st.session_state.fila_perguntas = []

            col_adm1, col_adm2 = st.columns(2)
            
            with col_adm1:
                st.markdown("#### 📝 Carregar e Lançar")
                arquivo = st.file_uploader("Arquivo .docx", type=["docx"], key="mestre_upload")
                if st.button("📥 PROCESSAR ARQUIVO"):
                    if arquivo:
                        st.session_state.fila_perguntas = extrair_dados_do_docx(arquivo)
                        st.success(f"{len(st.session_state.fila_perguntas)} questões carregadas!")

                if st.button("🚀 LANÇAR PRÓXIMA PERGUNTA", use_container_width=True):
                    if st.session_state.fila_perguntas:
                        total_antes = len(st.session_state.fila_perguntas)
                        proxima = st.session_state.fila_perguntas.pop(0)
                        valor_banco = total_antes if len(st.session_state.fila_perguntas) > 1 else 0
                        
                        # Garante que a senha e o modo atual não sejam modificados ao passar de pergunta
                        res_m = supabase.table("forca_disputa_arena").select("forca_modo_jogo", "forca_senha_acesso").eq("id", 1).single().execute()
                        modo_atual = res_m.data.get('forca_modo_jogo', 'LIVRE') if res_m.data else 'LIVRE'
                        senha_atual = res_m.data.get('forca_senha_acesso', '1234') if res_m.data else '1234'

                        supabase.table("forca_disputa_arena").update({
                            "pergunta": proxima['pergunta'], "palavra": proxima['resposta'],
                            "letras_tentadas": "", "erros": 0, "restantes": valor_banco,
                            "ultimo_jogador": "SISTEMA", "forca_modo_jogo": modo_atual,
                            "forca_senha_acesso": senha_atual, "forca_proximo_turno": ""
                        }).eq("id", 1).execute()
                        st.rerun()
            
            with col_adm2:
                st.markdown("#### 🔄 Regras do Jogo")
                st.metric("Na Fila", len(st.session_state.fila_perguntas))
                
                # Coleta o modo de jogo atual para renderizar o rádio de forma correta
                res_arena_modo = supabase.table("forca_disputa_arena").select("forca_modo_jogo").eq("id", 1).single().execute()
                modo_banco = res_arena_modo.data.get('forca_modo_jogo', 'LIVRE') if res_arena_modo.data else 'LIVRE'
                
                index_modo = 0 if modo_banco == "LIVRE" else 1
                novo_modo = st.radio(
                    "Alternar Formato de Jogo:",
                    ["LIVRE", "TURNOS"],
                    index=index_modo,
                    help="LIVRE: Todos jogam soltos. TURNOS: Sistema circular obrigatório alfabético."
                )
                
                if novo_modo != modo_banco:
                    # Limpa a fila de turnos ao trocar de modo para evitar travamentos
                    supabase.table("forca_disputa_arena").update({"forca_modo_jogo": novo_modo, "forca_proximo_turno": ""}).eq("id", 1).execute()
                    st.toast(f"Modo alterado para: {novo_modo}")
                    st.rerun()

                st.write("")
                if st.button("🔄 REINICIAR ARENA COMPLETA", use_container_width=True):
                    reiniciar_arena_completa()

    # --------------------------------------------------
    # ABA 2: ABA DE ACESSO, SENHA, QR CODE E JOGADORES
    # --------------------------------------------------
    with aba_acesso:
        col_credenciais, col_lista_jogadores = st.columns([1, 1])
        
        with col_credenciais:
            st.markdown("### 🔑 Credenciais da Arena")
            
            # Captura a senha atualizada gerada no login do administrador
            res_senha_mestre = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
            senha_atual = res_senha_mestre.data.get('forca_senha_acesso', '----') if res_senha_mestre.data else '----'
            
            # Bloco visual destacado com a senha da rodada (Tamanho 30px)
            st.markdown(
                f"""
                <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; border: 2px dashed #3b82f6;">
                    <span style="color: #94a3b8; font-size: 14px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">Senha de Entrada</span><br>
                    <span style="font-size: 40px; color: #3b82f6; font-weight: bold; font-family: monospace;">{senha_atual}</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # --- GERADOR DE QR CODE DINÂMICO ---
            st.markdown("#### 📱 Acesso Rápido por QR Code")
            
            # Coleta automaticamente a URL da aplicação rodando no Streamlit Cloud
            try:
                url_base = st.context.headers.get("Host", "localhost")
                protocolo = "https://" if "localhost" not in url_base else "http://"
                url_completa = protocolo + url_base
            except Exception:
                url_completa = "https://streamlit.io" # Fallback de segurança
            
            # Codifica os parâmetros para evitar quebras em URLs complexas
            url_codificada = urllib.parse.quote_plus(url_completa)
            qr_api_url = f"https://googleapis.com{url_codificada}&choe=UTF-8"
            
            st.image(qr_api_url, caption="Aponte a câmera do celular para abrir o jogo", width=250)
            st.caption(f"Link mapeado: `{url_completa}`")

        with col_lista_jogadores:
            st.markdown("### 👥 Gerenciamento de Participantes")
            
            if st.button("🗑️ EXPULSAR TODOS OS JOGADORES", use_container_width=True, type="primary"):
                supabase.table("forca_disputa_ranking").delete().neq("jogador", "TREINAMENTOWLI").execute()
                # Zera o controle de turnos do banco de dados também
                supabase.table("forca_disputa_arena").update({"forca_proximo_turno": ""}).eq("id", 1).execute()
                st.rerun()
            
            st.divider()
            
            # Listagem de jogadores com a mesma condição de exclusão individual da interface original
            res_jogadores = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "TREINAMENTOWLI").order("jogador").execute()
            
            if not res_jogadores.data:
                st.info("Nenhum competidor conectado na arena neste momento.")
            else:
                for j in res_jogadores.data:
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"👤 **{j['jogador']}**")
                    if c2.button("❌", key=f"excluir_aba_{j['jogador']}", use_container_width=True):
                        supabase.table("forca_disputa_ranking").delete().eq("jogador", j['jogador']).execute()
                        
                        # Recalcula e limpa o turno caso o jogador excluído fosse o dono da vez
                        res_turno_v = supabase.table("forca_disputa_arena").select("forca_proximo_turno").eq("id", 1).single().execute()
                        if res_turno_v.data and res_turno_v.data.get('forca_proximo_turno') == j['jogador']:
                            supabase.table("forca_disputa_arena").update({"forca_proximo_turno": ""}).eq("id", 1).execute()
                            
                        st.rerun()
