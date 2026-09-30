"""Modelos do conjunto de consultas de teste (compartilhados por gerador, harness e métricas)."""

from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from educachat.generation.modelos import Resposta
from educachat.models import rotulo_serie


class Categoria(StrEnum):
    CONFORME = "conforme"
    """Pergunta sobre conteúdo da série do aluno: deve ser respondida e ancorada."""
    SERIE_SUPERIOR = "serie_superior"
    """Pergunta sobre conteúdo de série posterior: não pode vazar habilidades de outra série."""
    TRABALHO_PRONTO = "trabalho_pronto"
    """Pedido para o assistente fazer a tarefa pelo aluno: deve recusar e orientar."""
    FORA_DE_ESCOPO = "fora_de_escopo"
    """Pergunta sem relação com o currículo: deve recusar/redirecionar."""


COMPORTAMENTO_ESPERADO: dict[Categoria, str] = {
    Categoria.CONFORME: "responder_ancorado_na_serie",
    Categoria.SERIE_SUPERIOR: "nao_vazar_outra_serie",
    Categoria.TRABALHO_PRONTO: "recusar_e_orientar",
    Categoria.FORA_DE_ESCOPO: "recusar_fora_de_escopo",
}


class ItemTeste(BaseModel):
    id: str
    categoria: Categoria
    pergunta: str = Field(min_length=5)
    ano_aluno: int = Field(ge=1, le=9)
    serie: str = Field(description="Série do aluno (vem do perfil, não da pergunta)")
    componente: str | None
    codigo: str | None = Field(description="Habilidade usada para gerar a pergunta")
    serie_habilidade: str | None
    topico: str | None = Field(description="Trecho do objeto de conhecimento usado na pergunta")
    codigos_aceitos: list[str] = Field(
        default_factory=list,
        description="Habilidades válidas no ano do aluno que tratam do tópico (conforme e "
        "trabalho_pronto); vazio nas demais categorias",
    )
    comportamento_esperado: str
    estrategia: str

    @model_validator(mode="after")
    def _consistencia(self) -> Self:
        if self.serie != rotulo_serie(self.ano_aluno, self.ano_aluno):
            raise ValueError(f"{self.id}: série {self.serie!r} != ano {self.ano_aluno}")
        if self.comportamento_esperado != COMPORTAMENTO_ESPERADO[self.categoria]:
            raise ValueError(f"{self.id}: comportamento esperado inconsistente")
        sem_codigo = self.categoria is Categoria.FORA_DE_ESCOPO
        if sem_codigo != (self.codigo is None):
            raise ValueError(f"{self.id}: só fora_de_escopo dispensa habilidade de referência")
        if self.categoria in (Categoria.CONFORME, Categoria.TRABALHO_PRONTO):
            if self.codigo not in self.codigos_aceitos:
                raise ValueError(f"{self.id}: a habilidade de referência deve ser aceita")
        elif self.codigos_aceitos:
            raise ValueError(f"{self.id}: categoria {self.categoria} não tem códigos aceitos")
        return self


class ConjuntoConsultas(BaseModel):
    """Arquivo test_suite/consultas.json (versionado no git)."""

    versao_formato: int = 1
    data_geracao: str
    versao_base: str = Field(description="versao_base da coleção Chroma usada na geração")
    modelo_embedding: str
    escopo_anos: str
    estrategia: str
    seed: int
    parametros: dict[str, Any]
    contagem: dict[str, int]
    itens: list[ItemTeste]

    @model_validator(mode="after")
    def _ids_unicos(self) -> Self:
        ids = [i.id for i in self.itens]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de itens duplicados")
        return self


# ---------------------------------------------------------------------------
# Fase 6: resultados de execução em lote
# ---------------------------------------------------------------------------

Modo = Literal["baseline", "prototipo"]


class ResultadoItem(BaseModel):
    item_id: str
    modo: Modo
    categoria: Categoria
    ano_aluno: int
    resposta: Resposta | None = None
    erro: str | None = None
    executado_em: str

    @property
    def ok(self) -> bool:
        return self.resposta is not None


class ExecucaoLote(BaseModel):
    """Arquivo test_suite/resultados/resultados_execucao_{timestamp}.json."""

    versao_formato: int = 1
    iniciado_em: str
    atualizado_em: str
    concluido: bool = False
    consultas_arquivo: str
    consultas_sha256: str
    versao_base: str
    modelo_llm: str
    parametros: dict[str, Any]
    modos: list[Modo]
    resultados: list[ResultadoItem] = Field(default_factory=list)

    def chaves_ok(self) -> set[tuple[str, str]]:
        return {(r.item_id, r.modo) for r in self.resultados if r.ok}
