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
# 2. LOGIN E ESTADO (COM TRAVA DE SEGURANÇA NO ADMIN)
# ==================================================
if "jogador" not in st.session_state:
    st.session_state.jogador = None

if "clique_bloqueado" not in st.session_state:
    st.session_state.clique_bloqueado = False

if not st.session_state.jogador:
    st.title("⚔️ Arena da Forca")
    
    # Seleção de Perfil para Entrada
    perfil = st.radio("Escolha seu perfil para entrar:", ["Jogador", "Mestre do Jogo (Admin)"])
    
    if perfil == "Mestre do Jogo (Admin)":
        st.info("Acesso restrito. Insira as credenciais do Mestre para assumir o controle.")
        # Solicita a credencial secreta do administrador de forma mascarada
        senha_admin = st.text_input("Digite a chave de acesso do Mestre:", type="password", key="input_senha_admin")
        
        if st.button("ENTRAR COMO MESTRE"):
            # Validação exata em maiúsculo para evitar problemas com Caps Lock
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
                
                # Impede que um jogador tente fraudar o ranking usando o nome do admin
                if nome_upper == "TREINAMENTOWLI":
                    st.error("Para entrar como administrador, selecione a opção 'Mestre do Jogo (Admin)' acima.")
                else:
                    try:
                        res_arena = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
                        senha_valida = res_arena.data.get('forca_senha_acesso', '1234') if res_arena.data else '1234'
                    except Exception:
                        senha_valida = '1234'

                    if senha_digitada.strip().upper() == senha_valida.upper():
                        st.session_state.jogador = nome_upper
                        check_user = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", nome_upper).execute()
                        
                        if not check_user.data:
                            supabase.table("forca_disputa_ranking").upsert(
                                {"jogador": nome_upper, "pontos": 0}, 
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
            return lista_jogadores[0]
            
        if jogador_atual in lista_jogadores:
            idx = lista_jogadores.index(jogador_atual)
            idx_proximo = (idx + 1) % len(lista_jogadores)
            return lista_jogadores[idx_proximo]
        else:
            return lista_jogadores[0]
    except Exception:
        return ""

def forçar_passagem_turno_por_tempo(jogador_punido):
    """Penaliza o jogador com -5 pontos por estourar o tempo e passa a vez."""
    try:
        # Desconta 5 pontos do jogador que deixou o tempo expirar
        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", jogador_punido).single().execute()
        if res_p.data:
            pts_atuais = res_p.data['pontos']
            # Evita pontuação negativa se preferir, ou desconta livremente:
            novo_pts = max(0, pts_atuais - 5)
            supabase.table("forca_disputa_ranking").update({"pontos": novo_pts}).eq("jogador", jogador_punido).execute()
        
        # Calcula o próximo da fila
        proximo = calcular_proximo_turno(jogador_punido)
        
        # Passa a vez no banco e reseta o cronômetro global da arena (now())
        supabase.rpc("set_timezone", {"tz": "America/Sao_Paulo"}).execute() # Garante fuso horário local
        supabase.table("forca_disputa_arena").update({
            "forca_proximo_turno": proximo,
            "forca_timestamp_turno": "now()"
        }).eq("id", 1).execute()
    except Exception:
        pass

def registrar_jogada(letra, jogo_atual):
    if st.session_state.jogador == "TREINAMENTOWLI":
        return

    # TRAVA REALTIME NO BANCO DE DADOS
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
    
    if letra in palavra_alvo:
        # ACERTOU: +5 pontos (Mantido original)
        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
        if res_p.data:
            pts_atuais = res_p.data['pontos']
            supabase.table("forca_disputa_ranking").update({"pontos": pts_atuais + 5}).eq("jogador", st.session_state.jogador).execute()
            st.toast(f"🎯 Boa! +5 pontos pela letra {letra}!")
    else:
        # ERROU: Vai para a forca
        novos_erros += 1
        # MODIFICAÇÃO: Se estiver no modo TURNOS, também perde 5 pontos
        if modo_jogo == "TURNOS":
            res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
            if res_p.data:
                pts_atuais = res_p.data['pontos']
                novo_pts = max(0, pts_atuais - 5)
                supabase.table("forca_disputa_ranking").update({"pontos": novo_pts}).eq("jogador", st.session_state.jogador).execute()
                st.toast(f"💥 Errou! -5 pontos na Arena.")
    
    # Passa o bastão e reseta o cronômetro atualizando para o momento exato do clique ("now()")
    proximo = calcular_proximo_turno(st.session_state.jogador)
    
    supabase.table("forca_disputa_arena").update({
        "letras_tentadas": novas_letras,
        "erros": novos_erros,
        "ultimo_jogador": st.session_state.jogador,
        "forca_proximo_turno": proximo,
        "forca_timestamp_turno": "now()"
    }).eq("id", 1).execute()

# ==================================================
# 4. INTERFACE DA ARENA
# ==================================================
from datetime import datetime, timezone

@st.fragment(run_every=2)
def arena_viva():
    st.session_state.clique_bloqueado = False

    res = supabase.table("forca_disputa_arena").select("*").eq("id", 1).single().execute()
    jogo = res.data
    if not jogo:
        st.warning("Aguardando o Administrador do Jogo iniciar...")
        return

    if jogo['pergunta'] != "Aguardando nova pergunta..." and jogo['erros'] < 6:
        if os.path.exists("musica.mp3"):
            st.audio("musica.mp3", format="audio/mp3", loop=True, autoplay=True)

    # CORREÇÃO: Restaurada a proporção exata [3, 1] do seu código original para evitar o erro do log
    col_jogo, col_rank = st.columns([3, 1])

    with col_jogo:
        # CORREÇÃO: Restaurada a proporção exata [1, 2] do seu código original para a imagem e o texto
        c_img, c_txt = st.columns([1, 2])
        erros_atuais = jogo.get('erros', 0)
        ultimo_player = jogo.get('ultimo_jogador', "SISTEMA")
        modo_jogo = jogo.get('forca_modo_jogo', "LIVRE")
        proximo_autorizado = jogo.get('forca_proximo_turno', "")
        timestamp_banco = jogo.get('forca_timestamp_turno', None)
        
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
                        res_p = supabase.table("forca_disputa_ranking").select("pontos").eq("jogador", st.session_state.jogador).single().execute()
                        pts = res_p.data['pontos'] if res_p.data else 0
                        supabase.table("forca_disputa_ranking").update({"pontos": pts + 10}).eq("jogador", st.session_state.jogador).execute()
                        st.toast(f"🏆 +10 pontos por vencer o desafio!")
                    st.session_state[id_palavra_atual] = True
                    
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

        # --- LÓGICA DE TURNOS E CÁLCULO DO CRONÔMETRO ---
        autorizado_a_jogar = True
        mensagem_turno = ""
        tempo_restante = 10
        
        if modo_jogo == "TURNOS" and not vitoria and erros_atuais < 6:
            if not proximo_autorizado or str(proximo_autorizado).strip() == "":
                mensagem_turno = "🔥 **Arena aberta!** Qualquer jogador cadastrado pode fazer o primeiro palpite."
                autorizado_a_jogar = True
            else:
                if timestamp_banco:
                    try:
                        hora_turno = datetime.fromisoformat(timestamp_banco.replace("Z", "+00:00"))
                        agora_utc = datetime.now(timezone.utc)
                        segundos_decorridos = int((agora_utc - hora_turno).total_seconds())
                        tempo_restante = max(0, 10 - segundos_decorridos)
                    except Exception:
                        tempo_restante = 10
                
                if tempo_restante <= 0:
                    forçar_passagem_turno_por_tempo(proximo_autorizado)
                    st.rerun()

                if str(st.session_state.jogador).strip() == str(proximo_autorizado).strip():
                    mensagem_turno = f"⚔️ **SUA VEZ, {st.session_state.jogador}!** Seu teclado está ativo. Responda rápido!"
                    autorizado_a_jogar = True
                else:
                    mensagem_turno = f"⏳ **AGUARDE A FILA!** É a vez do jogador: **{proximo_autorizado}**."
                    autorizado_a_jogar = False

        if mensagem_turno:
            st.info(mensagem_turno)
            if modo_jogo == "TURNOS" and proximo_autorizado and proximo_autorizado != "":
                st.progress(tempo_restante / 10, text=f"⏱️ Tempo restante para a jogada: {tempo_restante} segundos")

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

if st.session_state.jogador and st.session_state.jogador != "TREINAMENTOWLI":
    arena_viva()



# ==================================================
# 5. PAINEL DO ADMIN (TREINAMENTOWLI)
# ==================================================
if st.session_state.jogador == "TREINAMENTOWLI":
    st.title("⚔️ Painel do Mestre - Arena da Forca")
    
    # Criando as três abas totalmente independentes e organizadas
    aba_jogo, aba_acesso, aba_qrcode = st.tabs(["🎮 ARENA DO JOGO", "👥 CONTROLE DE PARTICIPANTES", "📱 QR CODE"])
    
    # Puxa a senha gerada para os jogadores comuns
    try:
        res_senha_mestre = supabase.table("forca_disputa_arena").select("forca_senha_acesso").eq("id", 1).single().execute()
        senha_atual = res_senha_mestre.data.get('forca_senha_acesso', '----') if res_senha_mestre.data else '----'
    except Exception:
        senha_atual = '----'
        
    # Captura a URL para o rodapé informativo
    try:
        url_base = st.context.headers.get("Host", "localhost")
        protocolo = "https://" if "localhost" not in url_base else "http://"
        url_completa = protocolo + url_base
    except Exception:
        url_completa = "https://streamlit.io"

    # --------------------------------------------------
    # ABA 1: GERENCIAMENTO DE PERGUNTAS E EXIBIÇÃO DA FORCA
    # --------------------------------------------------
    with aba_jogo:
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
    # ABA 2: GERENCIAMENTO E EXPULSÃO DE PARTICIPANTES
    # --------------------------------------------------
    with aba_acesso:
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
    # ABA 3: ABA EXCLUSIVA DO QR CODE GIGANTE (NATIVA E SEGUNDO AS REGRAS)
    # --------------------------------------------------
    with aba_qrcode:
        # Exibição da senha em destaque no topo da projeção
        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 25px; border-radius: 10px; text-align: center; margin-bottom: 25px; border: 2px dashed #3b82f6;">
                <span style="color: #94a3b8; font-size: 18px; text-transform: uppercase; font-weight: bold; letter-spacing: 2px;">Chave de Entrada</span><br>
                <span style="font-size: 70px; color: #3b82f6; font-weight: bold; font-family: monospace; letter-spacing: 6px;">{senha_atual}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # Criando colunas puras do Streamlit para centralizar e deixar a imagem gigante
        col_esq, col_centro, col_dir = st.columns([1, 4, 1])
        
        with col_centro:
            nome_arquivo_qr = "QRCode Forca.png"
            
            # Executa a verificação física do arquivo na pasta raiz do repositório
            if os.path.exists(nome_arquivo_qr):
                # Exibe de forma nativa e limpa a imagem estática ocupando o espaço máximo configurado
                st.image(
                    nome_arquivo_qr, 
                    caption="Aponte a câmera do celular para abrir a Arena", 
                    width=600
                )
            else:
                st.error(f"⚠️ O arquivo '{nome_arquivo_qr}' não foi encontrado no seu GitHub. Certifique-se de que o upload foi feito na pasta principal com esse nome exato.")

        st.write("")
        st.markdown(f"<p style='text-align: center; color: #64748b; font-family: monospace;'>Endereço da Arena: {url_completa}</p>", unsafe_allow_html=True)
