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
    caracteres = string.ascii_uppercase + string.digits
    return "".join(random.choice(caracteres) for _ in range(4))

# ==================================================
# 2. LOGIN E ESTADO (ATUALIZADO COM VÍNCULO DE AVATAR)
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

if "clique_bloqueado" not in st.session_state:
    st.session_state.clique_bloqueado = False

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    
    perfil = st.radio("Escolha seu perfil para entrar:", ["Jogador", "Mestre do Jogo (Admin)"])
    
    if perfil == "Mestre do Jogo (Admin)":
        st.info("Acesso restrito. Insira as credenciais do Mestre para assumir o controle.")
        senha_admin = st.text_input("Digite a chave de acesso do Mestre:", type="password", key="input_senha_admin")
        
        if st.button("ENTRAR COMO MESTRE"):
            if senha_admin and senha_admin.strip().upper() == "TREINAMENTOWLI":
                st.session_state.jogador = "TREINAMENTOWLI"
                nova_senha = gerar_senha_aleatoria()
                try:
                    supabase.table("forca_disputa_arena").update({"forca_senha_acesso": nova_senha}).eq("id", 1).execute()
                except Exception:
                    pass
                st.rerun()
            else:
                st.error("🔒 Chave de acesso do Mestre incorreta ou negada.")
                
    else:
        nome = st.text_input("Digite seu nome para entrar na Arena:", key="input_nome")
        senha_digitada = st.text_input("Digite a Senha da Arena (Fornecida pelo Mestre):", type="password", key="input_senha")
        
        if st.button("ENTRAR NA ARENA"):
            if nome and senha_digitada:
                nome_upper = nome.strip().upper()
                
                if nome_upper == "TREINAMENTOWLI":
                    st.error("Para entrar como administrador, selecione a opção 'Mestre do Jogo (Admin)' acima.")
                else:
                    try:
                        res_arena = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
                        senha_valida = res_arena.data.get('forca_senha_acesso', '1234') if res_arena.data else '1234'
                    except Exception:
                        senha_valida = '1234'

                    if senha_digitada.strip().upper() == sender_valida.upper() if 'sender_valida' in locals() else senha_digitada.strip().upper() == senha_valida.upper():
                        st.session_state.jogador = nome_upper
                        check_user = supabase.table("forca_disputa_ranking").select("*").eq("jogador", nome_upper).execute()
                        
                        if check_user.data:
                            st.toast(f"👋 Bem-vindo de volta, {nome_upper}!")
                        else:
                            # MODIFICAÇÃO: Descobre quantos usuários já entraram para definir o próximo avatar na fila
                            total_users = supabase.table("forca_disputa_ranking").select("jogador", count="exact").neq("jogador", "TREINAMENTOWLI").execute()
                            qtd_atual = total_users.count if total_users.count is not None else 0
                            
                            # O primeiro vira 1, o segundo 2, etc.
                            num_avatar = qtd_atual + 1 
                            
                            # Registra no banco guardando os pontos e o número do avatar dele
                            supabase.table("forca_disputa_ranking").upsert(
                                {"jogador": nome_upper, "pontos": 0, "forca_avatar_num": num_avatar}, 
                                on_conflict="jogador"
                            ).execute()
                        st.rerun()
                    else:
                        st.error("🔑 Senha incorreta. Digite a senha gerada pelo Mestre no telão.")
            else:
                st.warning("Por favor, preencha o seu nome e a senha da arena.")
    st.stop()

# ==================================================
# 3. LÓGICA DE JOGO
# ==================================================
def calcular_proximo_turno(jogador_atual):
    """Calcula estritamente quem é o próximo na ordem alfabética de inscritos."""
    try:
        res = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "TREINAMENTOWLI").order("jogador").execute()
        lista_jogadores = [r['jogador'] for r in res.data]
        
        if not lista_jogadores:
            return ""
        if len(lista_jogadores) == 1:
            return lista_jogadores
            
        if jogador_atual in lista_jogadores:
            idx = lista_jogadores.index(jogador_atual)
            idx_proximo = (idx + 1) % len(lista_jogadores)
            return lista_jogadores[idx_proximo]
        else:
            return lista_jogadores[0] if lista_jogadores else ""
    except Exception:
        return ""

def registrar_jogada(letra, jogo_atual):
    if st.session_state.jogador == "TREINAMENTOWLI":
        return

    # TRAVA REALTIME DE TURNO NO BANCO
    try:
        res_arena_atualizada = supabase.table("forca_disputa_arena").select("forca_modo_jogo", "forca_proximo_turno").eq("id", 1).single().execute()
        if res_arena_atualizada.data:
            modo_jogo_real = res_arena_atualizada.data.get('forca_modo_jogo', 'LIVRE')
            proximo_real = res_arena_atualizada.data.get('forca_proximo_turno', '')
            
            if modo_jogo_real == "TURNOS" and proximo_real and proximo_real != "":
                if st.session_state.jogador != proximo_real:
                    st.session_state.clique_bloqueado = False
                    return
    except Exception:
        return

    try:
        check = supabase.table("forca_disputa_ranking").select("jogador").eq("jogador", st.session_state.jogador).execute()
        if not check.data:
            st.session_state.jogador = None
            st.rerun()
            return
    except Exception:
        pass

    st.session_state.clique_bloqueado = True

    lista_antiga = jogo_atual['letras_tentadas']
    tentadas = [l.strip() for l in lista_antiga.split(",") if l.strip()]
    
    if letra in tentadas:
        st.session_state.clique_bloqueado = False
        return

    novas_letras = (lista_antiga + "," + letra) if lista_antiga else letra
    novos_erros = jogo_atual['erros']
    palavra_alvo = jogo_atual['palavra']
    modo_jogo = jogo_atual.get('forca_modo_jogo', 'LIVRE')
    
    # Identifica o nome da coluna de pontuação dinamicamente
    res_p = supabase.table("forca_disputa_ranking").select("*").eq("jogador", st.session_state.jogador).single().execute()
    col_pontos = "points" if "points" in res_p.data else "pontos"
    pts_atuais = res_p.data[col_pontos] if res_p.data else 0

    if letra in palavra_alvo:
        # ACERTOU: Ganha 5 pontos (Regra original)
        supabase.table("forca_disputa_ranking").update({col_pontos: pts_atuais + 5}).eq("jogador", st.session_state.jogador).execute()
        st.toast(f"🎯 Boa! +5 pontos pela letra {letra}!")
    else:
        # ERROU: Soma um erro na forca
        novos_erros += 1
        # NOVA REGRA: Se errar a letra jogando no formato TURNOS, perde 5 pontos
        if modo_jogo == "TURNOS":
            novo_pts = max(0, pts_atuais - 5)
            supabase.table("forca_disputa_ranking").update({col_pontos: novo_pts}).eq("jogador", st.session_state.jogador).execute()
            st.toast(f"💥 Letra incorreta! Você perdeu 5 pontos.")
    
    # Avança o bastão para o próximo da fila alfabética
    proximo = calcular_proximo_turno(st.session_state.jogador)
    
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
# 4. INTERFACE DA ARENA (CORRIGIDA E BLINDADA)
# ==================================================

@st.fragment(run_every=2)
def arena_viva():
    st.session_state.clique_bloqueado = False

    try:
        res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
        jogo = res.data
    except Exception:
        st.warning("Aguardando sincronização com a Arena...")
        return
        
    if not jogo:
        st.warning("Aguardando o Administrador do Jogo iniciar...")
        return

    if jogo['pergunta'] != "Aguardando nova pergunta..." and jogo['erros'] < 6:
        if os.path.exists("musica.mp3"):
            st.audio("musica.mp3", format="audio/mp3", loop=True, autoplay=True)

    # CORREÇÃO: Restaurada a proporção original 3:1 do seu primeiro código para evitar a quebra
    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        # CORREÇÃO: Restaurada a proporção original 1:2 do seu primeiro código para imagem e texto
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

            if vitoria and erros_atuais < 6:
                id_palavra_atual = f"vitoria_{palavra_alvo}_{contagem}"
                if id_palavra_atual not in st.session_state:
                    if st.session_state.jogador == ultimo_player and st.session_state.jogador != "TREINAMENTOWLI":
                        try:
                            res_p = supabase.table("forca_disputa_ranking").select("*").eq("jogador", st.session_state.jogador).single().execute()
                            col_pts = "points" if "points" in res_p.data else "pontos"
                            pts = res_p.data[col_pts] if res_p.data else 0
                            supabase.table("forca_disputa_ranking").update({col_pts: pts + 10}).eq("jogador", st.session_state.jogador).execute()
                            st.toast(f"🏆 +10 pontos por vencer o desafio!")
                        except Exception:
                            pass
                    st.session_state[id_palavra_atual] = True
                    
            if (vitoria or erros_atuais >= 6) and contagem == 0:
                try:
                    rank_final = supabase.table("forca_disputa_ranking").select("*").neq("jogador", "TREINAMENTOWLI").order("points" if "points" in jogo else "pontos", desc=True).execute().data
                except Exception:
                    rank_final = []
                if rank_final:
                    col_pts = "points" if "points" in rank_final[0] else "pontos"
                    max_pts = rank_final[0][col_pts]
                    vencedores = [r['jogador'] for r in rank_final if r[col_pts] == max_pts]
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
    
            texto_visual = "".join([f"{l} " if (l == " " or l in tentadas or erros_atuais >= 6) else "_ " for l in palavra_alvo])
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 15px;">
                    <code style="font-size: 20px; color: #ff4b4b; font-weight: bold;">{texto_visual}</code>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.caption(f"Última jogada por: **{ultimo_player}** | Formato: **{modo_jogo}**")

        # --- EXIBIÇÃO DE CONTROLE DE QUEM É A VEZ ---
        autorizado_a_jogar = True
        mensagem_turno = ""
        
        if modo_jogo == "TURNOS" and not vitoria and erros_atuais < 6:
            if not proximo_autorizado or str(proximo_autorizado).strip() == "":
                mensagem_turno = "🔥 **Arena aberta!** Qualquer jogador cadastrado pode fazer o primeiro palpite."
                autorizado_a_jogar = True
            else:
                if str(st.session_state.jogador).strip() == str(proximo_autorizado).strip():
                    mensagem_turno = f"⚔️ **SUA VEZ, {st.session_state.jogador}!** Seu teclado está ativo para jogar."
                    autorizado_a_jogar = True
                else:
                    mensagem_turno = f"⏳ **AGUARDE A FILA!** É a vez do jogador: **{proximo_autorizado}**."
                    autorizado_a_jogar = False

        if mensagem_turno:
            st.info(mensagem_turno)

        # --- TECLADO VIRTUAL OPERANTE ---
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
                is_admin = st.session_state.jogador == "TREINAMENTOWLI"
                
                botao_desabilitado = ja_foi or (not autorizado_a_jogar) or st.session_state.clique_bloqueado or is_admin
                
                if cols_tec[i % 9].button(letra, key=f"arena_tec_{letra}", disabled=botao_desabilitado, use_container_width=True):
                    st.session_state.clique_bloqueado = True
                    registrar_jogada(letra, jogo)
                    st.rerun()
        elif not (contagem == 0) and vitoria:
             st.info("✅ Palavra correta! Aguardando o Administrador...")

    with col_rank:
        st.markdown("### 🏆 Ranking")
        try:
            res_rank = supabase.table("forca_disputa_ranking").select("*").order("points" if "points" in jogo else "pontos", desc=True).execute()
            jogadores_faciais = [r for r in res_rank.data if r['jogador'] != "TREINAMENTOWLI"]
            
            for i, r in enumerate(jogadores_faciais[:10]):
                col_p = "points" if "points" in r else "pontos"
                num_avatar = r.get("forca_avatar_num", None)
                nome_avatar = f"AV{num_avatar}.png" if num_avatar else None
                
                # CORREÇÃO: Proporção definida 1:4 para evitar quebras no mini avatar
                c_av, c_rk = st.columns([1, 4])
                with c_av:
                    if nome_avatar and os.path.exists(nome_avatar):
                        st.image(nome_avatar, width=28)
                    else:
                        st.markdown("👤")
                with c_rk:
                    st.write(f"{i+1}º {r['jogador']}: {r[col_p]} pts")
        except Exception:
            st.write("Atualizando...")

if st.session_state.jogador and st.session_state.jogador != "TREINAMENTOWLI":
    arena_viva()


# ==================================================
# 5. PAINEL DO ADMIN (TREINAMENTOWLI) - BLOCO A
# ==================================================
if st.session_state.jogador == "TREINAMENTOWLI":
    st.title("⚔️ Painel do Mestre - Arena da Forca")
    
    # 1. Busca os dados atuais para verificar se a rodada terminou
    try:
        res_arena_check = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
        jogo_check = res_arena_check.data
    except Exception:
        jogo_check = None

    # Gatilho de fim de jogo
    arena_encerrada = False
    if jogo_check:
        erros_check = jogo_check.get('erros', 0)
        tentadas_check = [l.strip() for l in jogo_check['letras_tentadas'].split(",") if l.strip()]
        palavra_check = jogo_check['palavra']
        vitoria_check = all((letra == " " or letra in tentadas_check) for letra in palavra_check)
        
        if vitoria_check or erros_check >= 6:
            arena_encerrada = True

    # 2. Constrói a lista de abas dinamicamente
    # CORREÇÃO: Se o jogo acabou, colocamos o pódio em primeiro na lista para o Streamlit focar nele automaticamente!
    if arena_encerrada:
        nomes_abas = ["🏆 PODER DOS CAMPEÕES", "🎮 ARENA DO JOGO", "👥 CONTROLE DE PARTICIPANTES", "📱 QR CODE"]
    else:
        nomes_abas = ["🎮 ARENA DO JOGO", "👥 CONTROLE DE PARTICIPANTES", "📱 QR CODE"]
        
    # Declara o container de abas limpo e compatível com todas as versões do Streamlit
    abas = st.tabs(nomes_abas)
    
    # Coleta dados de credenciais estáveis para as demais abas
    try:
        res_senha_mestre = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
        senha_atual = res_senha_mestre.data.get('forca_senha_acesso', '----') if res_senha_mestre.data else '----'
    except Exception:
        senha_atual = '----'
        
    try:
        url_base = st.context.headers.get("Host", "localhost")
        protocolo = "https://" if "localhost" not in url_base else "http://"
        url_completa = protocolo + url_base
    except Exception:
        url_completa = "https://streamlit.io"

    # --------------------------------------------------
    # ABA DA ARENA DO JOGO (Se o jogo acabou, ela vira o índice 1. Se está ativo, vira índice 0)
    # --------------------------------------------------
    indice_arena = 1 if arena_encerrada else 0
    with abas[indice_arena]:
        arena_viva()
        
        st.write("")
        with st.expander("⚙️ LANÇAMENTO DE QUESTÕES E CONFIGURAÇÕES", expanded=True):
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
                        
                        res_m = supabase.table("forca_disputa_arena").select("forca_modo_jogo", "forca_senha_acesso").eq("id", 1).single().execute()
                        modo_atual = res_m.data.get('forca_modo_jogo', 'LIVRE') if res_m.data else 'LIVRE'
                        senha_atual_b = res_m.data.get('forca_senha_acesso', '1234') if res_m.data else '1234'

                        supabase.table("forca_disputa_arena").update({
                            "pergunta": proxima['pergunta'], "palavra": proxima['resposta'],
                            "letras_tentadas": "", "erros": 0, "restantes": valor_banco,
                            "ultimo_jogador": "SISTEMA", "forca_modo_jogo": modo_atual,
                            "forca_senha_acesso": senha_atual_b, "forca_proximo_turno": ""
                        }).eq("id", 1).execute()
                        st.rerun()
            
            with col_adm2:
                st.markdown("#### 🔄 Regras da Arena")
                st.metric("Na Fila", len(st.session_state.fila_perguntas))
                
                res_arena_modo = supabase.table("forca_disputa_arena").select("forca_modo_jogo").eq("id", 1).single().execute()
                modo_banco = res_arena_modo.data.get('forca_modo_jogo', 'LIVRE') if res_arena_modo.data else 'LIVRE'
                
                index_modo = 0 if modo_banco == "LIVRE" else 1
                novo_modo = st.radio(
                    "Alternar Formato de Jogo:",
                    ["LIVRE", "TURNOS"],
                    index=index_modo,
                    help="LIVRE: Todos jogam livre. TURNOS: Ordem circular estrita obrigatória."
                )
                
                if novo_modo != modo_banco:
                    supabase.table("forca_disputa_arena").update({"forca_modo_jogo": novo_modo, "forca_proximo_turno": ""}).eq("id", 1).execute()
                    st.toast(f"Modo alterado para: {novo_modo}")
                    st.rerun()

                st.write("")
                if st.button("🔄 REINICIAR ARENA COMPLETA", use_container_width=True):
                    reiniciar_arena_completa()


    # --------------------------------------------------
    # ABA 1: GERENCIAMENTO E EXPULSÃO DE PARTICIPANTES
    # --------------------------------------------------
    with abas[1]:
        st.markdown("### 👥 Gerenciamento de Participantes na Sala")
        
        if st.button("🗑️ EXPULSAR TODOS OS JOGADORES DA ARENA", use_container_width=True, type="primary"):
            supabase.table("forca_disputa_ranking").delete().neq("jogador", "TREINAMENTOWLI").execute()
            supabase.table("forca_disputa_arena").update({"forca_proximo_turno": ""}).eq("id", 1).execute()
            st.rerun()
            
        st.write("")
        
        res_jogadores = supabase.table("forca_disputa_ranking").select("jogador").neq("jogador", "TREINAMENTOWLI").order("jogador").execute()
        
        if not res_jogadores.data:
            st.info("Nenhum competidor conectado na arena neste momento.")
        else:
            for j in res_jogadores.data:
                c1, c2 = st.columns(2)
                c1.markdown(f"👤 **{j['jogador']}**")
                if c2.button("❌ EXPULSAR", key=f"excluir_aba_{j['jogador']}", use_container_width=True):
                    supabase.table("forca_disputa_ranking").delete().eq("jogador", j['jogador']).execute()
                    
                    res_turno_v = supabase.table("forca_disputa_arena").select("forca_proximo_turno").eq("id", 1).single().execute()
                    if res_turno_v.data and res_turno_v.data.get('forca_proximo_turno') == j['jogador']:
                        supabase.table("forca_disputa_arena").update({"forca_proximo_turno": ""}).eq("id", 1).execute()
                        
                    st.rerun()

    # --------------------------------------------------
    # ABA 2: ABA EXCLUSIVA DO QR CODE GIGANTE
    # --------------------------------------------------
    with abas[2]:
        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 25px; border-radius: 10px; text-align: center; margin-bottom: 25px; border: 2px dashed #3b82f6;">
                <span style="color: #94a3b8; font-size: 18px; text-transform: uppercase; font-weight: bold; letter-spacing: 2px;">Chave de Entrada</span><br>
                <span style="font-size: 70px; color: #3b82f6; font-weight: bold; font-family: monospace; letter-spacing: 6px;">{senha_atual}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        col_esq, col_centro, col_dir = st.columns([1, 2, 1])
        with col_centro:
            nome_arquivo_qr = "QRCode Forca.png"
            if os.path.exists(nome_arquivo_qr):
                st.image(nome_arquivo_qr, use_container_width=True)
            else:
                st.error(f"⚠️ O arquivo '{nome_arquivo_qr}' não foi encontrado no seu GitHub.")

        st.write("")
        st.markdown(f"<p style='text-align: center; color: #64748b; font-family: monospace;'>Endereço da Arena: {url_completa}</p>", unsafe_allow_html=True)

    # --------------------------------------------------
    # ABA 3: ABA EXCLUSIVA DO AVATAR VENCEDOR (PÓDIO GIGANTE)
    # --------------------------------------------------
    if arena_encerrada:
        with abas[3]:
            st.markdown("<h1 style='text-align: center; color: #ffb703;'>🏆 PÓDIO DA ARENA DA FORCA 🏆</h1>", unsafe_allow_html=True)
            st.write("")
            
            try:
                res_vencedores = supabase.table("forca_disputa_ranking").select("*").neq("jogador", "TREINAMENTOWLI").order("points" if "points" in (jogo_check if jogo_check else {}) else "pontos", desc=True).execute().data
            except Exception:
                res_vencedores = []
                
            if res_vencedores:
                col_p_v = "points" if "points" in res_vencedores[0] else "pontos"
                max_pts_v = res_vencedores[0][col_p_v]
                
                # Coleta todos os primeiros colocados (trata cenários de empates)
                lista_campeoes = [r for r in res_vencedores if r[col_p_v] == max_pts_v]
                
                col_v_esq, col_v_centro, col_v_dir = st.columns([1, 2, 1])
                
                with col_v_centro:
                    for campeao in lista_campeoes:
                        num_av_v = campeao.get("forca_avatar_num", None)
                        arquivo_av_v = f"AV{num_av_v}.png" if num_av_v else None
                        
                        if arquivo_av_v and os.path.exists(arquivo_av_v):
                            st.image(arquivo_av_v, width=380)
                        else:
                            st.markdown("<h1 style='text-align: center; font-size: 100px;'>👤</h1>", unsafe_allow_html=True)
                        
                        st.markdown(
                            f"""
                            <div style="text-align: center; margin-top: 15px; margin-bottom: 30px;">
                                <h2 style="font-size: 36px; color: #10b981; margin-bottom: 5px;">👑 {campeao['jogador']}</h2>
                                <h3 style="font-size: 24px; color: #64748b; font-family: monospace;">GRANDE CAMPEÃO COM {max_pts_v} PTS</h3>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
