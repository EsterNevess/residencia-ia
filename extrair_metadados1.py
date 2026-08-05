import os
import json
from pathlib import Path
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODELO = os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
BASE_URL = "https://api.groq.com/openai/v1"

if not API_KEY:
    raise ValueError("❌ Chave GROQ_API_KEY não encontrada no arquivo .env!")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)


class MetadadosBasicos(BaseModel):
    titulo: str = Field(
        description="Título principal do artigo ou documento."
    )
    autores: list[str] = Field(
        description="Lista com os nomes dos autores do documento."
    )
    ano: int = Field(
        description="Ano de publicação do documento no formato AAAA."
    )


def extrair_metadados_basicos(caminho_md: Path) -> dict:
    """
    Lê o arquivo .md e extrai titulo, autores e ano respeitando os limites da API.
    """
    conteudo_md = caminho_md.read_text(encoding="utf-8")


    LIMITE_CARACTERES = 18000
    if len(conteudo_md) > LIMITE_CARACTERES:
        conteudo_md = conteudo_md[:LIMITE_CARACTERES]

    completion = client.beta.chat.completions.parse(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um assistente especializado em extração de informações de artigos acadêmicos. "
                    "Extraia com precisão o título, a lista de autores e o ano de publicação do documento."
                )
            },
            {
                "role": "user",
                "content": f"Analise o documento abaixo e extraia os metadados solicitados:\n\n{conteudo_md}"
            }
        ],
        response_format=MetadadosBasicos
    )

    resultado_estruturado = completion.choices[0].message.parsed
    return resultado_estruturado.model_dump()



if __name__ == "__main__":
    pasta_aula = Path("AULA_02/MARKDOWN")
    arquivos_md = list(pasta_aula.glob("*.md"))
    
    if not arquivos_md:
        print(f"❌ Nenhum arquivo .md encontrado na pasta {pasta_aula}!")
    else:
        print(f"🔍 Encontrados {len(arquivos_md)} arquivo(s) .md. Extraindo metadados básicos...\n")

    for arquivo in arquivos_md:
        print(f"📄 Processando: {arquivo.name}...")
        try:
            dados = extrair_metadados_basicos(arquivo)
            print("✅ Extração concluída:")
            print(json.dumps(dados, indent=2, ensure_ascii=False))
            print("-" * 50)
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo.name}: {e}\n")