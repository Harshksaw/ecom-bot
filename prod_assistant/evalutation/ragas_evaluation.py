from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper

from ragas.embeddings import LangchainEmbeddingWrapper
from ragas.metrics import LLMContextPrecisionWithoutReference, ResponseRelevancy
import grpc.experimental.aio as grpc_aio
grpc_aio.init_grpc_aio()

model_loader = ModelLoader()

def evaluate_context_precision():
    """_summary_
    """
    pass


def evaluate_response_relevancy(query):
    """_summary_
    query (_type_): _description_
    """
    pass

