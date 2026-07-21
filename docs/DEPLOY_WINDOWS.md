# Documentação Operacional de Implantação - Windows Server 2019

Este documento descreve o procedimento operacional para implantação e execução do servidor WSGI **Waitress** para a aplicação **Django SST Freedom** em ambiente de produção Windows Server 2019.

---

## 1. Visão Geral da Arquitetura

- **Desenvolvimento Local:**
  - Continua utilizando `python manage.py runserver` (ex: `127.0.0.1:8000` ou `8800`).
  - `DEBUG=True` no `.env` local.
- **Servidor de Produção (Windows Server 2019):**
  - **Servidor WSGI:** Waitress (`waitress-serve`).
  - **Endereço de Escuta:** `127.0.0.1:8800` (exclusivamente loopback).
  - **Acesso Externo:** Gerenciado via **Cloudflare Tunnel** apontando para `http://127.0.0.1:8800` (domínio público: `https://sst.freedom.dev.br`).
  - **Arquivos Estáticos:** Servidos via **WhiteNoise**.
  - **Caminho do Projeto no Servidor:** `C:\03_PYTHON\13_SST\sst_freedom`
  - **Ambiente Virtual:** `C:\03_PYTHON\13_SST\sst_freedom\.venv`

---

## 2. Passos para Implantação no Servidor (Após Git Pull)

Abrir o **PowerShell** no servidor Windows Server 2019 e executar os comandos sequencialmente:

```powershell
# 1. Navegar até a raiz do projeto
cd C:\03_PYTHON\13_SST\sst_freedom

# 2. Atualizar dependências (inclui Waitress)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Validar a integridade da aplicação Django
.\.venv\Scripts\python.exe manage.py check

# 4. Coletar arquivos estáticos (WhiteNoise)
.\.venv\Scripts\python.exe manage.py collectstatic --noinput

# 5. Executar o script de inicialização de produção
powershell -ExecutionPolicy Bypass -File .\scripts\start_production.ps1
```

---

## 3. Testes e Verificação Operacional

Com o processo do Waitress rodando, em outra janela do PowerShell no servidor, execute os testes abaixo:

### Teste de Conectividade de Porta
```powershell
Test-NetConnection 127.0.0.1 -Port 8800
```
*Resultado esperado:* `TcpTestSucceeded : True`

### Teste de Requisição HTTP Local
```powershell
Invoke-WebRequest http://127.0.0.1:8800 -UseBasicParsing
```
*Resultado esperado:* Código HTTP 200 (ou redirecionamento 302 para Login).

---

## 4. Controle e Encerrar o Processo

- O script `scripts/start_production.ps1` mantém o processo do Waitress em primeiro plano no terminal.
- Para parar a execução manualmente, pressione **`Ctrl + C`** na janela do terminal onde o script está rodando.

---

## 5. Próximos Passos (Serviço do Windows)

Em uma etapa posterior (após validação manual do Waitress), o script `.\scripts\start_production.ps1` poderá ser registrado como um Serviço do Windows (utilizando ferramentas como NSSM ou WinSW) para garantir inicialização automática no boot do sistema operacional.
