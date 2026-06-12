# Entrega Aula 01 — Grupo 02

## Estrutura

- `entrega-grupo-02-aula01.md`: documento principal da entrega.
- `diagramas/arquitetura-qc-aula01.png`: diagrama da arquitetura de alto nível.
- `diagramas/arquitetura-qc-aula01.drawio`: arquivo editável do diagrama.
- `diagramas/arquitetura-qc-aula01-bonus.png`: diagrama bônus multi-cloud.
- `diagramas/arquitetura-qc-aula01-bonus.drawio`: arquivo editável do diagrama bônus.
- `terraform/`: código Terraform do exercício 3.1.
- `bicep/main.bicep`: código Bicep do exercício 3.2.

## Como visualizar os diagramas

Os arquivos `.drawio` podem ser abertos em https://app.diagrams.net/.

## Como executar o Terraform

```bash
cd terraform
terraform init
terraform plan -var="meu_ip=$(curl -s ifconfig.me)"
terraform apply -var="meu_ip=$(curl -s ifconfig.me)"
```