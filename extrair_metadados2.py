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

class DetalhesMetodologicos(BaseModel):
    metodo: str = Field(
        description="Descrição sucinta do método, abordagem ou tipo de pesquisa (ex: revisão sistemática, estudo de caso, experimento)."
    )
    amostra: str = Field(
        description="Descrição da amostra, corpus de dados, quantidade de usuários, documentos ou dados analisados (ex: 50 artigos, 1000 tweets, N/A)."
    )
    metrica: str = Field(
        description="Métricas de avaliação, variáveis, critérios de análise ou indicadores utilizados na pesquisa."
    )
    limitacoes: str = Field(
        description="Limitações do estudo indicadas pelos autores ou desafios identificados durante a pesquisa."
    )



def extrair_detalhes(caminho_md: Path) -> dict:
    """
    Lê o arquivo .md e extrai metodo, amostra, metrica e limitacoes respeitando os limites da API.
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
                    "Você é um especialista em análise metodológica de artigos acadêmicos. "
                    "Sua tarefa é extrair com precisão e síntese o método, a amostra, as métricas "
                    "e as limitações descritas no documento."
                )
            },
            {
                "role": "user",
                "content": f"Analise o documento abaixo e extraia as informações metodológicas solicitadas:\n\n{conteudo_md}"
            }
        ],
        response_format=DetalhesMetodologicos
    )

    resultado_estruturado = completion.choices[0].message.parsed
    return resultado_estruturado.model_dump()



if __name__ == "__main__":
    pasta_aula = Path("AULA_02/MARKDOWN")
    arquivos_md = list(pasta_aula.glob("*.md"))
    
    if not arquivos_md:
        print(f"❌ Nenhum arquivo .md encontrado na pasta {pasta_aula}!")
    else:
        print(f"🔍 Encontrados {len(arquivos_md)} arquivo(s) .md. Extraindo detalhes metodológicos...\n")

    for arquivo in arquivos_md:
        print(f"📄 Processando: {arquivo.name}...")
        try:
            dados = extrair_detalhes(arquivo)
            print("✅ Análise metodológica concluída:")
            print(json.dumps(dados, indent=2, ensure_ascii=False))
            print("-" * 50)
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo.name}: {e}\n")