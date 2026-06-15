import csv
import random
from datetime import date, timedelta


def gerar_arquivo(nome_arquivo, data_inicio):
    with open(nome_arquivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["periodo", "valor"])

        for _ in range(1000):
            dia = data_inicio + timedelta(days=random.randint(0, 27))
            valor = round(random.uniform(50, 1500), 2)
            writer.writerow([dia.isoformat(), valor])


gerar_arquivo("logs_compras_jan.csv", date(2026, 1, 1))
gerar_arquivo("logs_compras_fev.csv", date(2026, 2, 1))
gerar_arquivo("logs_compras_mar.csv", date(2026, 3, 1))

print("Arquivos gerados com sucesso.")
