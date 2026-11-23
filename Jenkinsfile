// Pipeline de deploy da Vinheria Agnello
pipeline {
    agent any

    environment {
        PUBLICACAO  = '/publicacao'
        // Segredo usado SO nos testes; o de producao fica no .env, fora do Git
        JWT_SEGREDO = 'segredo-somente-para-testes-1234567890'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }
        stage('Build') {
            steps {
                echo 'Deploy da Vinheria'
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r servicos/pedidos/requirements.txt
                    python -m py_compile servicos/rastreamento/app.py servicos/pedidos/app.py
                    echo "Build OK: microsservicos Rastreamento e Pedidos compilados"
                '''
            }
        }
        stage('Testes') {
            steps {
                sh '. .venv/bin/activate && python -m unittest discover -s testes -v'
            }
        }
        stage('Seguranca') {
            steps {
                sh '''
                    echo "Verificando se ha segredos no repositorio..."
                    if git ls-files | grep -E '(^|/)\\.env$'; then echo "ERRO: .env versionado"; exit 1; fi
                    if git grep -n "BEGIN .*PRIVATE KEY"; then echo "ERRO: chave privada no codigo"; exit 1; fi
                    echo "Nenhum segredo encontrado no codigo"
                '''
            }
        }
        stage('Deploy') {
            steps {
                sh '''
                    DESTINO="$PUBLICACAO/releases/build-$BUILD_NUMBER"
                    mkdir -p "$DESTINO"
                    cp -r servicos "$DESTINO/"
                    rm -rf "$PUBLICACAO/atual" && cp -r "$DESTINO" "$PUBLICACAO/atual"
                    COMMIT=$(git rev-parse --short HEAD)
                    DATA=$(TZ=America/Sao_Paulo date '+%d/%m/%Y %H:%M')
                    sed -e "s|{{BUILD}}|$BUILD_NUMBER|g" -e "s|{{COMMIT}}|$COMMIT|g" -e "s|{{DATA}}|$DATA|g" \
                        infra/web/index.template.html > "$PUBLICACAO/index.html"
                    echo "Publicado em $DESTINO"
                    ls -la "$PUBLICACAO" "$PUBLICACAO/releases"
                '''
            }
        }
    }

    post {
        success { echo 'Deploy concluido: abra http://localhost:8088 (www.vinheria.local)' }
        failure { echo 'Pipeline falhou: nada foi publicado' }
    }
}
