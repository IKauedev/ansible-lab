# Ansible Lab

Laboratório local para estudar e testar Ansible. O Ansible roda no WSL (Ubuntu 22.04) e gerencia 3 containers Docker que fazem o papel de servidores, acessados por SSH.

```
 WSL (nó de controle)                     Docker
┌──────────────────────┐   SSH    ┌─────────────────────────┐
│ ansible / playbooks  │ ───────► │ web1  (nginx)     :2201 │
│ inventário dinâmico  │          │ web2  (nginx)     :2202 │
│ ansible-vault        │          │ db1   (postgres)  :2203 │
└──────────────────────┘          └─────────────────────────┘
```

## O que é o Ansible

Ferramenta de automação de infraestrutura. Você descreve em YAML o estado desejado dos servidores (pacotes, arquivos, usuários, serviços) e o Ansible leva todos a esse estado por SSH, sem instalar agente. É idempotente: rodar de novo só altera o que estiver diferente.

## Requisitos

- Windows com WSL2 e uma distro Ubuntu (`Ubuntu-22.04`)
- Docker acessível de dentro do WSL
- Ansible instalado em um venv no WSL (`~/ansible-lab/.venv`, criado com `uv`)

Fora do projeto, no WSL, ficam:

| Arquivo | Para quê |
|---|---|
| `~/.ssh/ansible-lab` | chave SSH privada do lab |
| `~/.ansible-vault-pass` | senha do Ansible Vault |

Eles ficam fora do projeto de propósito. O drive `E:` não guarda permissões de arquivo, e o SSH exige chave com `600`.

## Estrutura

```
ansible.cfg                     configuração do Ansible
docker-compose.yml              os 3 containers do lab
docker/Dockerfile               imagem Ubuntu com sshd, python3 e sudo
inventory/
  docker_inventory.py           inventário dinâmico (lê os containers)
  group_vars/
    all.yml                     variáveis de todos os hosts
    web.yml                     variáveis do grupo web
    db/vars.yml                 variáveis do grupo db
    db/vault.yml                senha do banco, criptografada (Vault)
roles/
  common/                       utilitários básicos (acl, curl, procps, iproute2)
  nginx/                        instala o nginx e publica uma página por template
  postgresql/                   instala o PostgreSQL, cria usuário e banco
playbooks/
  site.yml                      teste básico: ping, facts e /etc/motd
  stack.yml                     sobe a stack: banco primeiro, depois web
  status.yml                    relatório de processos, portas e serviços
```

## Como iniciar

```bash
# 1. Entrar no WSL como o usuário que tem a chave e o venv
wsl -d Ubuntu-22.04 -u ikauedev

# 2. Preparar o ambiente
cd /mnt/e/workspace/ansible-dev
export ANSIBLE_CONFIG=$PWD/ansible.cfg
source ~/ansible-lab/.venv/bin/activate

# 3. Subir os containers e conferir
docker compose up -d
ansible all -m ping

# 4. Aplicar a stack e ver o estado
ansible-playbook playbooks/stack.yml
ansible-playbook playbooks/status.yml
```

O `ANSIBLE_CONFIG` é necessário porque o Ansible ignora o `ansible.cfg` em pastas gravíveis por todos, como o `/mnt/e`.

Os containers não têm systemd, então nginx e PostgreSQL não sobem sozinhos quando o container reinicia. O `stack.yml` os inicia de novo.

## Inventário dinâmico

O `inventory/docker_inventory.py` lista os containers em execução que tenham o label `ansible.group` e monta os grupos e as portas SSH. Para criar um host novo, adicione um serviço no `docker-compose.yml`:

```yaml
web3: {image: ansible-lab-node, container_name: lab-web3, hostname: web3, ports: ["2204:22"], labels: {ansible.group: web}}
```

Depois rode `docker compose up -d`. O host aparece em `ansible-inventory --graph`, sem editar mais nada.

## Playbooks

| Playbook | O que faz |
|---|---|
| `site.yml` | `ping`, mostra o SO e cria o `/etc/motd` nos hosts |
| `stack.yml` | instala PostgreSQL no `db` e nginx nos `web`; cada web serve uma página com o próprio nome |
| `status.yml` | mostra por host os processos, as portas em escuta e se o nginx e o PostgreSQL respondem |

Rode o `stack.yml` duas vezes: na segunda, o resultado deve ser `changed=0`.

## Ansible Vault

A senha do banco fica em `inventory/group_vars/db/vault.yml`, criptografada. A senha do vault é lida de `~/.ansible-vault-pass` (configurada no `ansible.cfg`).

```bash
ansible-vault view inventory/group_vars/db/vault.yml
ansible-vault edit inventory/group_vars/db/vault.yml
ansible-vault encrypt_string 'segredo' --name 'minha_var'
```

Faça backup da senha do vault: sem ela, não dá para recuperar o `vault.yml`.

## Comandos úteis

```bash
ansible-inventory --graph                          # grupos e hosts
ansible all -m command -a "ps -eo pid,user,comm"   # processos de todos os nodes
ansible web -m command -a "curl -s localhost"      # página servida pelo nginx
ansible-playbook playbooks/stack.yml --check --diff # simula sem alterar nada
ansible-doc ansible.builtin.apt                    # documentação de um módulo
ansible-lint playbooks/                            # análise estática
```

Acessar um container:

```bash
docker exec -it lab-web1 bash
ssh -i ~/.ssh/ansible-lab -p 2201 ansible@127.0.0.1
```

No `ssh`, use o caminho completo da chave se estiver logado como `root` (o `~` vira `/root`).

## Resetar o lab

```bash
docker compose down && docker compose up -d
ansible-playbook playbooks/stack.yml
```

## Ideias para evoluir

- Permitir que os web acessem o PostgreSQL (`listen_addresses` e `pg_hba.conf`)
- Balanceador de carga nginx na frente de web1 e web2
- Mais distribuições (Debian, Rocky Linux) para treinar playbooks portáteis
- Testar as roles com Molecule
- Painel web em Python com `ansible-runner`
