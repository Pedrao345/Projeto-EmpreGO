import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from mysql.connector import Error
from config import *
from db_functions import *
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = SECRET_KEY
# Configurações de upload
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB

# Função para verificar se o arquivo tem uma extensão permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

#Rota da página inicial (TODOS ACESSAM)
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

#Rota da página Login
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
        

#ROTA DO ADM (Dono do projeto!)
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
    #Verificar se tem uma sessão
    if not session:
        return redirect('/login')
    
    #Se não for ADM, deve ser empresa
    if not 'adm' in session:
        return redirect('/empresa')
    
    #Acesso ao formuário de cadastro
    if request.method == 'GET':
        return render_template('cadastrar_empresa.html')
    
    #Tratando os dados vindos do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input (request.form['cnpj'])
        telefone = limpar_input (request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar se todos os campos estão preenchidos
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastrar_empresa.html', msg_erro="Todos os campos são obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'INSERT INTO empresa (nome_empresa,cnpj,telefone,email,senha) VALUES (%s,%s,%s,%s,%s)'
            cursor.execute(comandoSQL, (nome_empresa,cnpj,telefone,email,senha))
            conexao.commit() #Para comandos DML
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('cadastrar_empresa.html', msg_erro="Esse e-mail já existe!")
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

#Tratando os dados vindos do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input (request.form['cnpj'])
        telefone = limpar_input (request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar se todos os campos estão preenchidos
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('editar_empresa.html', msg_erro="Todos os campos são obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE empresa
            SET nome_empresa=%s, cnpj=%s, telefone=%s, email=%s, senha=%s
            WHERE id_empresa = %s;
            '''
            cursor.execute(comandoSQL, (nome_empresa,cnpj,telefone,email,senha,id_empresa))
            conexao.commit() #Para comandos DML
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('editar_empresa.html', msg_erro="Esse e-mail já existe!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor,conexao)

#ROTA PARA ATIVAR OU DESATIVAR A EMPRESA
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
        #Se a empresa estiver sendo desativada, as vagas também serão
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
        conexao, cursor = conectar_db()
        #EXCLUINDO AS VAGAS RELACIONADAS NA EMPRESA EXCLUIDA
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa=%s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()

        #EXCLUIR O CADASTRO DA EMPRESA
        comandoSQL = 'DELETE FROM empresa WHERE id_empresa=%s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        return redirect('/adm')
    except Error as erro:
        return f"Erro de BD: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally:
        encerrar_db(cursor, conexao)

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
        salario = limpar_input (request.form['salario'])

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
        salario = request.form['salario']
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

@app.route("/excluir_vaga/<int:id_vaga>")
def excluir_vaga(id_vaga):
    if not session:
        return redirect('/login')
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db
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
# Rota para exibir o formulário de candidatura e fazer upload do currículo - GET
@app.route('/candidatar_vaga/<int:id_vaga>', methods=['GET'])
def candidatar_vaga(id_vaga):
    # Aqui você deve buscar a vaga correspondente no banco de dados ou em outro lugar
    # No caso, como você não está usando banco de dados, vamos criar uma vaga fictícia
    vaga = {
        'id_vaga': id_vaga,
        'titulo': 'Vaga de Desenvolvedor Web',  # Exemplo de título
        'descricao': 'Desenvolvedor com experiência em Python e Flask'  # Exemplo de descrição
    }
    
    # Passa a vaga para o template
    return render_template('candidatar_vaga.html', vaga=vaga)


# Rota para a candidatura a vaga (Upload de currículo) - POST
@app.route('/candidatar_vaga/<int:id_vaga>', methods=['POST'])
def enviar_candidatura(id_vaga):
    nome = request.form.get('nome')
    email = request.form.get('email')
    curriculo = request.files.get('curriculo')
    
    if not nome or not email or not curriculo:
        flash('Todos os campos são obrigatórios!', 'error')
        return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))

    # Verifica se o arquivo tem uma extensão permitida
    if curriculo and allowed_file(curriculo.filename):
        try:
            # Salvar o currículo na pasta de uploads com um nome único
            nome_arquivo = f"{id_vaga}_{curriculo.filename}"
            curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))

            # Mensagem de sucesso
            flash('Currículo enviado com sucesso!', 'success')
            return redirect(url_for('index'))  # Redireciona para a página inicial após o envio

        except Exception as erro:
            flash(f'Ocorreu um erro ao salvar o currículo: {erro}', 'error')
            return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))  # Retorna à página de candidatura em caso de erro
    else:
        flash('Formato de arquivo inválido! Apenas PDF, DOC, DOCX e TXT são permitidos.', 'error')
        return redirect(url_for('candidatar_vaga', id_vaga=id_vaga))  # Retorna à página de candidatura se o arquivo for inválido
@app.route('/buscar_vagas', methods=['GET'])
def buscar_vagas():
    cursor = None  # Inicializa a variável cursor
    conexao = None  # Inicializa a variável conexão
    try:
        word = request.args.get('q', '')  # Captura o termo de busca, padrão é vazio
        if word:  # Só faz a consulta se o termo de pesquisa não estiver vazio
            comandoSQL = '''
            SELECT vaga.*, empresa.nome_empresa
            FROM vaga
            JOIN empresa ON vaga.id_empresa = empresa.id_empresa
            WHERE vaga.titulo LIKE %s AND vaga.status = 'ativa'
            ORDER BY vaga.id_vaga DESC;
            '''
            conexao, cursor = conectar_db()  # Conecta ao banco e obtém o cursor
            cursor.execute(comandoSQL, (f"%{word}%",))
            vagas_buscadas = cursor.fetchall()
            return render_template('buscar_vaga.html', vagas=vagas_buscadas, word=word)  # Renderiza a página completa
        return render_template('buscar_vaga.html', vagas=[], word=word)  # Retorna página sem resultados

    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        # Garante que o cursor e a conexão sejam fechados, se existirem
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()





 

    

#Rota de logout (Encerra)
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

#Final do código
if __name__ == '__main__':
    app.run(debug=True)