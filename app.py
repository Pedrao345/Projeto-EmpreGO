import traceback
from flask import Flask, flash, render_template, request, redirect, send_from_directory, session, url_for, current_app
from mysql.connector import Error 
from werkzeug.utils import secure_filename
from config import *
import os
from db_functions import * #Funções do banco de dados

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER']='uploads/'

# Configuração para permitir extensões específicas
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Rota da página inicial, todos acessam
@app.route('/')
def index():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False

    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('index.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#Rota da página login
# ROTA DA PÁGINA DE LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        if 'adm' in session:
            return redirect('/adm')
        else:
            return redirect('/empresa')

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        if not email or not senha:  # Corrigi aqui para verificar ambos os campos corretamente
            erro = "Os campos precisam estar preenchidos!"
            return render_template('login.html', msg_erro=erro)

        if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
            session['adm'] = True
            return redirect('/adm')

        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE email = %s AND senha = %s'
            cursor.execute(comandoSQL, (email, senha))
            empresa = cursor.fetchone()

            if not empresa:
                return render_template('login.html', msgerro='E-mail e/ou senha estão errados!')

            # Acessar os dados como dicionário
            if empresa['status'] == 'inativa':
                return render_template('login.html', msgerro='Empresa desativada! Procure o administrador!')

            session['id_empresa'] = empresa['id_empresa']
            session['nome_empresa'] = empresa['nome_empresa']
            return redirect('/empresa')
        
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA DA PÁGINA DO ADMIN
@app.route('/adm')
def adm():
    #Se não houver sessão ativa
    if not session:
        return redirect('/login')
    #Se não for o administrador
    if not 'adm' in session:
        return redirect('/empresa')
  
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM Empresa WHERE status = "ativa"'
        cursor.execute(comandoSQL)
        empresas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM Empresa WHERE status = "inativa"'
        cursor.execute(comandoSQL)
        empresas_inativas = cursor.fetchall()

        return render_template('adm.html', empresas_ativas=empresas_ativas, empresas_inativas=empresas_inativas)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/cadastrar_empresa', methods=['POST','GET'])
def cadastrar_empresa():
    # Verifica se tem uma sessão
    if not session:
        return redirect('/login')
    # Se não for o ADM (Deve ser alguma empresa)
    if not 'adm' in session:
        return redirect('/empresa')

    # Acesso ao formulário de cadastro
    if request.method == 'GET':
        return render_template('cadastrar_empresa.html')
    
    # Tratando os dados vindos do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        # Verifica se todos os campos estão preenchidos (Em uma situação real seriam adicionados verificações para os campos)
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastro_empresa.html', 
            msg_erro="Todos os campos são obrigatórios")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'INSERT INTO empresa (nome_empresa,cnpj,telefone,email,senha) VALUES (%s,%s,%s,%s,%s)' # Trata a falha de segurança 'sql injection'
            cursor.execute(comandoSQL, (nome_empresa,cnpj,telefone,email,senha))
            conexao.commit() # Quando usamos comando DML presisa-se usar o commit no BackEnd
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('cadastrar_empresa.html', msg_erro="Esse E-mail já existe!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor,conexao)

@app.route('/editar_empresa/<int:id_empresa>', methods=['GET','POST'])
def editar_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (id_empresa,))
            empresa = cursor.fetchone()
            return render_template('editar_empresa.html',empresa=empresa)
        except Error as erro:
            return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor, conexao)
    
        # Tratando os dados vindos do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        # Verifica se todos os campos estão preenchidos (Em uma situação real seriam adicionados verificações para os campos)
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('editar_empresa.html', 
            msg_erro="Todos os campos são obrigatórios")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE empresa
            SET nome_empresa=%s, cnpj=%s, telefone=%s, email=%s, senha=%s
            WHERE id_empresa = %s;
            '''
            cursor.execute(comandoSQL, (nome_empresa,cnpj,telefone,email,senha,id_empresa))
            conexao.commit() # Quando usamos comando DML presisa-se usar o commit no BackEnd
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('editar_empresa.html', msg_erro="Esse E-mail já existe!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor,conexao)

# Rota para ativa/desativar empresa
@app.route('/status_empresa/<int:id_empresa>')
def status(id_empresa):
    if not session:
        return redirect('/login')
    if not session['adm']:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        status_empresa = cursor.fetchone()
        if status_empresa['status'] == 'ativa':
            novo_status = 'inativa'
        else:
            novo_status = 'ativa'
        
        comandoSQL = 'UPDATE empresa SET status=%s WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (novo_status, id_empresa))
        conexao.commit()

        # Se a empresa estiver sendo desativada, as vagas também serão
        if novo_status == 'inativa':
            comandoSQL = 'UPDATE vaga SET status = %s WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (novo_status,id_empresa))
            conexao.commit()
        return redirect('/adm')
    except Error as erro:  
        return f"Erro de BD: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/excluir_empresa/<int:id_empresa>')
def excluir_empresa(id_empresa):
    if not session:
        return redirect('/login')
    if not session['adm']:
        return redirect('/login')

    try:
        print(f"Iniciando exclusão da empresa {id_empresa}")
        conexao, cursor = conectar_db()

        # Obter os caminhos dos arquivos de currículos associados à empresa
        comandoSQL = '''
            SELECT curriculo
            FROM candidato
            JOIN vaga ON candidato.id_vaga = vaga.id_vaga
            WHERE vaga.id_empresa = %s
        '''
        cursor.execute(comandoSQL, (id_empresa,))
        curriculos = cursor.fetchall()
        
        print(f"Currículos encontrados: {curriculos}")

        # Excluir arquivos de currículo da pasta 'uploads'
        pasta_uploads = os.path.join(os.getcwd(), 'uploads')  # Caminho absoluto para 'uploads'
        for curriculo in curriculos:
            if 'curriculo' in curriculo:  # Verifica se a chave 'curriculo' está presente no dicionário
                arquivo_curriculo = curriculo['curriculo']  # Obtém o valor associado à chave 'curriculo'
                caminho_arquivo = os.path.join(pasta_uploads, arquivo_curriculo)
                print(f"Verificando arquivo: {caminho_arquivo}")
                if os.path.exists(caminho_arquivo):
                    try:
                        os.remove(caminho_arquivo)  # Exclui o arquivo
                        print(f"Arquivo {caminho_arquivo} excluído com sucesso")
                    except Exception as e:
                        print(f"Erro ao excluir arquivo {caminho_arquivo}. Detalhes: {str(e)}")
                        return f"Erro ao excluir arquivo {caminho_arquivo}. Detalhes: {str(e)}"
                else:
                    print(f"Arquivo não encontrado: {caminho_arquivo}")
            else:
                print(f"Currículo mal formatado ou chave ausente: {curriculo}")

        # Excluir candidatos relacionados às vagas da empresa
        comandoSQL = '''
            DELETE FROM candidato
            WHERE id_vaga IN (SELECT id_vaga FROM vaga WHERE id_empresa = %s)
        '''
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        print(f"Candidatos da empresa {id_empresa} excluídos")

        # Excluir vagas relacionadas à empresa
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        print(f"Vagas da empresa {id_empresa} excluídas")

        # Excluir a empresa
        comandoSQL = 'DELETE FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        print(f"Empresa {id_empresa} excluída")
        
        return redirect('/adm')
    except Exception as erro:
        erro_str = traceback.format_exc()
        print(f"Erro de BackEnd: {erro_str}")
        return f"Erro de BackEnd: {erro_str}"
    finally:
        encerrar_db(cursor, conexao)


# Rota página da empresa
#ROTA DA PÁGINA DE GESTÃO DAS EMPRESAS
@app.route('/empresa')
def empresa():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    id_empresa = session['id_empresa']
    nome_empresa = session['nome_empresa']

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "ativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "inativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_inativas = cursor.fetchall()

        return render_template('empresa.html', nome_empresa=nome_empresa, vagas_ativas=vagas_ativas, vagas_inativas=vagas_inativas)         
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

# Rota de logout (encerra a sessão)
@app.route('/logout')
def logout():
    #logout
    session.clear()
    return redirect('/')

@app.route('/cadastrar_vaga', methods=['POST','GET'])
def cadastrar_vaga():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')
    
    if request.method == 'GET':
        return render_template('cadastrar_vaga.html')
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = ''
        local = request.form['local']
        salario = ''
        salario = limpar_input(request.form['salario'])
        id_empresa = session['id_empresa']

        if not titulo or not descricao or not formato or not tipo:
            return render_template('cadastrar_vaga.html', msg_erro="Os campos obrigatório precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Vaga (titulo, descricao, formato, tipo, local, salario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_empresa))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA VER DETALHES DA VAGA
@app.route('/sobre_vaga/<int:id_vaga>')
def sobre_vaga(id_vaga):
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
        WHERE vaga.id_vaga = %s;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        
        if not vaga:
            return redirect('/')
        
        return render_template('sobre_vaga.html', vaga=vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EDITAR A VAGA
@app.route('/editar_vaga/<int:id_vaga>', methods=['GET','POST'])
def editarvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM vaga WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()
            return render_template('editar_vaga.html', vaga=vaga)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = request.form['local']
        salario = limpar_input(request.form['salario'])

        if not titulo or not descricao or not formato or not tipo:
            return redirect('/empresa')
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE vaga SET titulo=%s, descricao=%s, formato=%s, tipo=%s, local=%s, salario=%s
            WHERE id_vaga = %s;
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_vaga))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA ALTERAR O STATUS DA VAGA
@app.route("/status_vaga/<int:id_vaga>")
def statusvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM vaga WHERE id_vaga = %s;'
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        if vaga['status'] == 'ativa':
            status = 'inativa'
        else:
            status = 'ativa'

        comandoSQL = 'UPDATE vaga SET status = %s WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (status, id_vaga))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)
#ROTA PARA EXCLUIR VAGA
@app.route("/excluir_vaga/<int:id_vaga>")
def excluirvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'DELETE FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        comandoSQL = 'DELETE FROM vaga WHERE id_vaga = %s AND status = "inativa"'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao) 
@app.route('/procurar_vagas')
def procurar_vagas():
    try:
        word = request.args.get('word')  
        comandoSQL = '''    
        select vaga.*, empresa.nome_empresa 
        from vaga 
        join empresa on vaga.id_empresa = empresa.id_empresa
        where vaga.titulo like %s and vaga.status = 'ativa'
        order by vaga.id_vaga desc;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (f"%{word}%",)) 
        vagas_buscadas = cursor.fetchall()
        return render_template('buscar_vaga.html', vagas=vagas_buscadas, word=word)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/candidatar_vaga/<int:id_vaga>', methods=['GET', 'POST'])
def candidatar_vaga(id_vaga):

    if session:
        return redirect ('/')

    try:
        # Recuperar informações da vaga no banco de dados
        conexao, cursor = conectar_db()
        cursor.execute('SELECT * FROM vaga WHERE id_vaga = %s', (id_vaga,))
        vaga = cursor.fetchone()  # Pega os detalhes da vaga

        # Verificar se a vaga foi encontrada
        if not vaga:
            return "Vaga não encontrada", 404

        if request.method == 'GET':
            return render_template('candidatar_vaga.html', vaga=vaga)

        if request.method == 'POST':
            nome = request.form['nome']
            email = request.form['email']
            telefone = limpar_input(request.form['telefone'])
            curriculo = request.files['curriculo']  # Obter o arquivo do currículo

            # Verificar se todos os campos obrigatórios foram preenchidos
            if not nome or not email or not telefone or not curriculo:
                flash('Todos os campos são obrigatórios!', 'error')
                return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))

            # Verificar se o formato do arquivo de currículo é permitido
            if curriculo and allowed_file(curriculo.filename):
                try:
                    # Gerar o nome seguro do arquivo de currículo
                    nome_arquivo = f"{id_vaga}_{secure_filename(curriculo.filename)}"

                    # Salvar o arquivo no diretório de uploads
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)  # Cria o diretório de uploads, se não existir
                    curriculo.save(os.path.join(upload_folder, nome_arquivo))

                    # Inserir o candidato no banco de dados com o nome do arquivo de currículo
                    cursor.execute('INSERT INTO candidato (nome, email, telefone, curriculo, id_vaga) VALUES (%s, %s, %s, %s, %s)', 
                                   (nome, email, telefone, nome_arquivo, id_vaga))
                    conexao.commit()

                    # Redirecionar para a página de agradecimento ou outra página após o envio
                    return redirect(url_for('candidatura_enviada'))

                except Exception as erro:
                    flash(f'Ocorreu um erro ao salvar o currículo: {erro}', 'error')
                    return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))
            else:
                flash("Formato de arquivo inválido! Apenas PDF, DOC, DOCX e TXT são permitidos.", "error")
                return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))

    except Exception as e:
        flash(f"Erro: {e}", "error")
        return redirect(url_for('index'))
    finally:
        encerrar_db(cursor, conexao)

# Rota da página de agradecimento (após o envio do currículo)
@app.route('/candidatura_enviada')
def candidatura_enviada():
    return render_template('candidatura_enviada.html')  # Renderiza a página de agradecimento


@app.route('/candidatos/<int:id_vaga>')
def ver_candidatos(id_vaga):
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT nome, email, telefone, id_candidato FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        candidatos = cursor.fetchall()

        # Verifica se há candidatos encontrados
        if not candidatos:
            candidatos = []

        return render_template('candidatos.html', candidatos=candidatos, id_vaga=id_vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/download/<int:id_candidato>')
def download_curriculo(id_candidato):
    try:
        conexao, cursor = conectar_db()
        # Buscar o caminho do currículo no banco de dados
        cursor.execute('SELECT curriculo FROM candidato WHERE id_candidato = %s', (id_candidato,))
        candidato = cursor.fetchone()

        if not candidato:
            return "Candidato não encontrado", 404

        nome_arquivo = candidato['curriculo']
        caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)

        # Verificar se o arquivo existe
        if not os.path.exists(caminho_arquivo):
            return "Arquivo não encontrado", 404

        # Enviar o arquivo para download
        return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo, as_attachment=True)

    except Exception as erro:
        return f"Erro ao baixar o currículo: {erro}", 500
    finally:
        encerrar_db(cursor, conexao)
@app.route('/excluir/<int:id_candidato>/<int:id_vaga>', methods=['GET'])
def excluir_candidato(id_candidato, id_vaga):
    try:
        conexao, cursor = conectar_db()

        # Primeiro, obtemos o nome do arquivo do currículo do candidato
        comandoSQL = "SELECT curriculo FROM candidato WHERE id_candidato = %s"
        cursor.execute(comandoSQL, (id_candidato,))
        candidato = cursor.fetchone()

        if candidato:
            # Caminho completo do arquivo na pasta 'uploads'
            caminho_arquivo = os.path.join('uploads', candidato['curriculo'])

            # Verificar se o arquivo existe e excluir
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)

            # Excluir o candidato do banco de dados
            comandoSQL = "DELETE FROM candidato WHERE id_candidato = %s"
            cursor.execute(comandoSQL, (id_candidato,))
            conexao.commit()  # Commit para garantir a exclusão no banco de dados

        # Redirecionar para a página de candidatos da vaga específica
        return redirect(url_for('ver_candidatos', id_vaga=id_vaga))

    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)





# Final do código
if __name__ == '__main__':
    app.run(debug=True)